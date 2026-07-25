import os
import json
import math
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

from app.ml.gnn_cascade import RailwayGNN, CascadeLoss

def build_railway_topology(num_nodes: int = 50, num_edges: int = 140):
    """
    Builds a synthetic Indian Railways network graph topology.
    Nodes: 50 major junction stations (NDLS, BCT, HWH, MAS, CNB, etc.)
    Edges: 140 bi-directional track section links
    """
    torch.manual_seed(2026)
    np.random.seed(2026)

    # Node features: [platform_count, congestion_score, avg_dwell_time, current_delay, schedule_density, track_capacity, signaling_type, weather_impact]
    x = torch.zeros((num_nodes, 8), dtype=torch.float)
    x[:, 0] = torch.randint(2, 16, (num_nodes,)).float() # platforms
    x[:, 1] = torch.rand(num_nodes) * 0.8 + 0.1 # congestion
    x[:, 2] = torch.randint(2, 20, (num_nodes,)).float() # dwell min
    x[:, 3] = torch.randint(0, 45, (num_nodes,)).float() # current delay
    x[:, 4] = torch.rand(num_nodes) * 0.9 + 0.1 # schedule density
    x[:, 5] = torch.randint(20, 100, (num_nodes,)).float() # track capacity
    x[:, 6] = torch.randint(1, 4, (num_nodes,)).float() # signal type
    x[:, 7] = torch.rand(num_nodes) * 0.5 # weather

    # Build connected ring + random shortcuts for railway junctions
    edges = []
    for i in range(num_nodes):
        edges.append((i, (i + 1) % num_nodes))
        edges.append(((i + 1) % num_nodes, i))

    while len(edges) < num_edges * 2:
        u = np.random.randint(0, num_nodes)
        v = np.random.randint(0, num_nodes)
        if u != v and (u, v) not in edges:
            edges.append((u, v))
            edges.append((v, u))

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    num_e = edge_index.size(1)

    # Edge features: [length_km, speed_limit_kmh, electrification_type, gradient, maintenance_index, traffic_class]
    edge_attr = torch.zeros((num_e, 6), dtype=torch.float)
    edge_attr[:, 0] = torch.randint(10, 150, (num_e,)).float() # length
    speeds = np.random.choice([80.0, 100.0, 110.0, 130.0], size=num_e)
    edge_attr[:, 1] = torch.tensor(speeds, dtype=torch.float)
    edge_attr[:, 2] = torch.randint(0, 2, (num_e,)).float()
    edge_attr[:, 3] = torch.rand(num_e) * 0.05
    edge_attr[:, 4] = torch.rand(num_e) * 0.7 + 0.3
    edge_attr[:, 5] = torch.randint(1, 5, (num_e,)).float()

    # Targets:
    # 1. delay_minutes: [delay_30min, delay_60min, delay_90min]
    # 2. cascade_reached: binary indicator if delay > 25min propagates
    delay_targets = torch.zeros((num_nodes, 3), dtype=torch.float)
    delay_targets[:, 0] = x[:, 3] * 1.1 + torch.randn(num_nodes) * 2
    delay_targets[:, 1] = x[:, 3] * 1.25 + torch.randn(num_nodes) * 3
    delay_targets[:, 2] = x[:, 3] * 1.40 + torch.randn(num_nodes) * 4
    delay_targets = torch.clamp(delay_targets, min=0.0)

    cascade_reached = (delay_targets[:, 1] > 20.0).float()

    return {
        "x": x,
        "edge_index": edge_index,
        "edge_attr": edge_attr,
        "target": {
            "delay_minutes": delay_targets,
            "cascade_reached": cascade_reached,
        }
    }

def train_gnn():
    print("[1/4] Building Indian Railways 50-station network topology graph...")
    graph = build_railway_topology(50, 140)

    x = graph["x"]
    edge_index = graph["edge_index"]
    edge_attr = graph["edge_attr"]
    target = graph["target"]

    print("[2/4] Initializing RailwayGNN (3-layer GraphSAGE + GATConv)...")
    model = RailwayGNN(
        node_feat_dim=8,
        edge_feat_dim=6,
        hidden_dim=128,
        n_sage_layers=3,
        n_gat_heads=4,
        dropout=0.1
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)
    criterion = CascadeLoss(alpha=0.6)

    print("[3/4] Training RailwayGNN for 120 epochs...")
    model.train()
    for epoch in range(1, 121):
        optimizer.zero_grad()
        out = model(x, edge_index, edge_attr, time_of_day=0.5)
        loss = criterion(out, target)
        loss.backward()
        optimizer.step()

        if epoch % 20 == 0 or epoch == 120:
            print(f"  Epoch {epoch:3d}/120 | Loss: {loss.item():.4f}")

    # Validation evaluation
    model.eval()
    with torch.no_grad():
        out = model(x, edge_index, edge_attr, time_of_day=0.5)
        pred_prob = out["cascade_probability"].numpy()
        true_label = target["cascade_reached"].numpy()
        pred_binary = (pred_prob > 0.50).astype(int)

        from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
        val_auc = float(roc_auc_score(true_label, pred_prob))
        val_f1 = float(f1_score(true_label, pred_binary))
        val_prec = float(precision_score(true_label, pred_binary))
        val_rec = float(recall_score(true_label, pred_binary))

    print(f"\n  GNN Validation Metrics:")
    print(f"    Validation AUC: {val_auc:.4f}")
    print(f"    Validation F1: {val_f1:.4f}")
    print(f"    Precision: {val_prec:.4f}")
    print(f"    Recall: {val_rec:.4f}")

    print("[4/4] Saving PyTorch weights & GNN metrics JSON...")
    base_dir = Path(__file__).resolve().parent.parent
    artifacts_dir = base_dir / "app" / "ml" / "artifacts"
    reports_dir = base_dir / "reports"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    weights_path = artifacts_dir / "gnn_cascade.pt"
    torch.save({
        "state_dict": model.state_dict(),
        "config": {
            "node_feat_dim": 8,
            "edge_feat_dim": 6,
            "hidden_dim": 128,
            "n_sage_layers": 3,
            "n_gat_heads": 4,
        },
        "val_metrics": {
            "val_auc": round(val_auc, 4),
            "val_f1": round(val_f1, 4),
        }
    }, weights_path)

    metrics_report = {
        "model": "RailwayGNN (3-layer GraphSAGE + GATConv, 128-dim hidden)",
        "topology": "50 Junction Stations, 140 Direct Track Section Links",
        "num_parameters": sum(p.numel() for p in model.parameters()),
        "val_auc": round(val_auc, 4),
        "val_f1": round(val_f1, 4),
        "val_precision": round(val_prec, 4),
        "val_recall": round(val_rec, 4),
        "weights_size_bytes": os.path.getsize(weights_path),
        "trained_at": datetime.now(timezone.utc).isoformat()
    }

    report_path = reports_dir / "gnn_metrics.json"
    with open(report_path, "w") as f:
        json.dump(metrics_report, f, indent=2)

    print(f"Artifacts saved:")
    print(f"  PyTorch Weights: {weights_path} ({os.path.getsize(weights_path) / 1024:.2f} KB)")
    print(f"  Metrics JSON: {report_path}")

if __name__ == "__main__":
    train_gnn()
