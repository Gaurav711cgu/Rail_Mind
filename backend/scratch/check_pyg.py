import sys
print("Python version:", sys.version)
try:
    print("Attempting to import torch...")
    import torch
    print("torch version:", torch.__version__)
    
    print("Attempting to import torch_geometric...")
    import torch_geometric
    print("torch_geometric version:", torch_geometric.__version__)
    from torch_geometric.nn import SAGEConv, GATConv
    print("Successfully imported SAGEConv and GATConv")
except Exception as e:
    print("Failed to import or use torch_geometric:", e)
