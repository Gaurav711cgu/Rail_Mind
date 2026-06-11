"""
RailwayGNN — Graph Neural Network for delay cascade prediction.
Includes PyTorch Geometric SAGEConv/GATConv implementations with robust native PyTorch fallback layers.
"""

import math
import torch
import torch.nn as nn
from typing import Dict, Any

# Try to import torch_geometric; define fallback classes if unavailable
import sys
try:
    # Force fallback on macOS because of PyG C++ extension deadlocks under pytest runner
    if sys.platform == "darwin":
        raise ImportError("Forcing fallback on macOS to avoid pytest deadlocks")
    from torch_geometric.nn import SAGEConv, GATConv
    HAS_PYG = True
except ImportError:
    HAS_PYG = False

    class SAGEConv(nn.Module):
        """Native PyTorch fallback for SAGEConv."""
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.lin_l = nn.Linear(in_channels, out_channels)
            self.lin_r = nn.Linear(in_channels, out_channels)
            self.act = nn.GELU()

        def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
            # Simple neighborhood aggregation: x_new = lin_l(x) + lin_r(mean_neighbors(x))
            num_nodes = x.size(0)
            deg = torch.zeros(num_nodes, dtype=torch.float, device=x.device)
            adj_sum = torch.zeros((num_nodes, x.size(1)), dtype=torch.float, device=x.device)
            
            if edge_index.numel() > 0:
                src, dst = edge_index[0], edge_index[1]
                adj_sum.index_add_(0, dst, x[src])
                deg.index_add_(0, dst, torch.ones_like(src, dtype=torch.float))
                
            deg = torch.clamp(deg, min=1.0).unsqueeze(1)
            aggregated = adj_sum / deg
            return self.act(self.lin_l(x) + self.lin_r(aggregated))

    class GATConv(nn.Module):
        """Native PyTorch fallback for GATConv."""
        def __init__(self, in_channels: int, out_channels: int, heads: int = 1, dropout: float = 0.0, edge_dim: int = None):
            super().__init__()
            self.heads = heads
            self.out_channels = out_channels
            self.lin = nn.Linear(in_channels, out_channels * heads)
            if edge_dim:
                self.lin_edge = nn.Linear(edge_dim, out_channels * heads)
            else:
                self.lin_edge = None
            self.att = nn.Parameter(torch.Tensor(1, heads, 2 * out_channels))
            nn.init.xavier_uniform_(self.att)

        def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor = None) -> torch.Tensor:
            num_nodes = x.size(0)
            h = self.lin(x).view(num_nodes, self.heads, self.out_channels)
            
            # Simple self-attention mechanism
            if edge_index.numel() > 0:
                src, dst = edge_index[0], edge_index[1]
                h_src = h[src]
                h_dst = h[dst]
                
                # Combine source and destination features
                cat = torch.cat([h_src, h_dst], dim=-1)
                alpha = (cat * self.att).sum(dim=-1)
                alpha = torch.nn.functional.leaky_relu(alpha, 0.2)
                
                # Softmax over neighborhood
                alpha_exp = torch.exp(alpha)
                denom = torch.zeros((num_nodes, self.heads), device=x.device)
                denom.index_add_(0, dst, alpha_exp)
                denom = torch.clamp(denom, min=1e-6)
                
                alpha_soft = alpha_exp / denom[dst]
                
                # Weighted aggregation
                out = torch.zeros((num_nodes, self.heads, self.out_channels), device=x.device)
                out.index_add_(0, dst, h_src * alpha_soft.unsqueeze(-1))
            else:
                out = h
                
            return out.view(num_nodes, self.heads * self.out_channels)


class RailwayGNN(nn.Module):
    """
    GraphSAGE backbone with GAT attention heads for cascade prediction.
    
    Design Choices:
    - Inductive message passing using SAGEConv.
    - Learns section propagation weights using GATConv.
    - Normalizes temporal visibility/conditions using time embeddings.
    """
    
    def __init__(
        self,
        node_feat_dim: int = 8,      # station features
        edge_feat_dim: int = 6,      # section features
        hidden_dim: int = 128,
        n_sage_layers: int = 3,
        n_gat_heads: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        
        self.node_proj = nn.Linear(node_feat_dim, hidden_dim)
        
        self.sage_layers = nn.ModuleList([
            SAGEConv(hidden_dim, hidden_dim) for _ in range(n_sage_layers)
        ])
        
        self.gat = GATConv(
            hidden_dim, hidden_dim // n_gat_heads,
            heads=n_gat_heads, dropout=dropout, edge_dim=edge_feat_dim
        )
        
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(hidden_dim) for _ in range(n_sage_layers + 1)
        ])
        
        self.time_embed = nn.Sequential(
            nn.Linear(2, hidden_dim // 4),
            nn.GELU(),
        )
        
        self.delay_head = nn.Sequential(
            nn.Linear(hidden_dim + hidden_dim // 4, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 3),   # [delay_30min, delay_60min, delay_90min]
        )
        
        self.cascade_prob_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
        
    def forward(
        self,
        x: torch.Tensor,                  # [N, node_feat_dim]
        edge_index: torch.Tensor,          # [2, E]
        edge_attr: torch.Tensor,           # [E, edge_feat_dim]
        time_of_day: float,                # Normalized float (0.0 to 1.0)
        disruption_node_mask: torch.Tensor # [N]
    ) -> Dict[str, torch.Tensor]:
        
        # 1. Temporal encoding: sin/cos representing diurnal cycles
        t = torch.tensor([
            math.sin(time_of_day * 2 * math.pi),
            math.cos(time_of_day * 2 * math.pi)
        ], dtype=torch.float, device=x.device)
        
        time_feat = self.time_embed(t).unsqueeze(0).expand(x.size(0), -1)
        
        # 2. Project node features
        h = self.node_proj(x)
        
        # 3. Inductive Message Passing
        for i, sage in enumerate(self.sage_layers):
            h_new = sage(h, edge_index)
            h = self.layer_norms[i](h + h_new)  # residual connection
            h = torch.nn.functional.gelu(h)
            
        # 4. GAT Attention Layer
        h_gat = self.gat(h, edge_index, edge_attr)
        h = self.layer_norms[-1](h + h_gat)
        
        # 5. Concatenate temporal embeddings
        h_with_time = torch.cat([h, time_feat], dim=-1)
        
        # 6. Prediction Heads
        delay_pred = self.delay_head(h_with_time)
        cascade_prob = self.cascade_prob_head(h).squeeze()
        
        return {
            "delay_minutes": delay_pred,
            "cascade_probability": cascade_prob,
        }


class CascadeLoss(nn.Module):
    """
    Multi-task loss function combining delay regression (Huber Loss)
    and cascade reach probability classification (BCE Loss).
    """
    def __init__(self, alpha: float = 0.7):
        super().__init__()
        self.alpha = alpha
        self.delay_loss = nn.HuberLoss(delta=15.0)  # Robust against outliers
        self.cascade_loss = nn.BCELoss()
        
    def forward(self, pred: Dict[str, torch.Tensor], target: Dict[str, torch.Tensor]) -> torch.Tensor:
        l_delay = self.delay_loss(pred["delay_minutes"], target["delay_minutes"])
        l_cascade = self.cascade_loss(pred["cascade_probability"], target["cascade_reached"])
        return self.alpha * l_delay + (1.0 - self.alpha) * l_cascade
