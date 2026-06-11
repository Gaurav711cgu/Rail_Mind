import torch
import math
from app.ml.gnn_cascade import RailwayGNN

print("Initializing tensors...")
# 10 stations, 8 features per station
x = torch.randn(10, 8)
# 12 sections (edges)
edge_index = torch.randint(0, 10, (2, 12))
# 6 features per edge
edge_attr = torch.randn(12, 6)
disruption_mask = torch.zeros(10, dtype=torch.bool)
disruption_mask[3] = True  # Station 3 is disrupted

print("Initializing RailwayGNN model...")
model = RailwayGNN(node_feat_dim=8, edge_feat_dim=6, hidden_dim=64, n_sage_layers=2)

print("Calling model.forward()...")
out = model(x, edge_index, edge_attr, time_of_day=0.35, disruption_node_mask=disruption_mask)

print("Model forward completed successfully!")
print("delay_minutes shape:", out["delay_minutes"].shape)
print("cascade_probability shape:", out["cascade_probability"].shape)
