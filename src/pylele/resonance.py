#!/usr/bin/env python

"""
import trimesh
import numpy as np
from scipy.sparse.linalg import eigsh

# 1. Load and repair STL
mesh = trimesh.load("cavity.stl")
assert mesh.is_watertight, "Mesh must be watertight"

# 2. Convert to FEM mesh (simplified 2D example)
vertices = mesh.vertices[:, :2]  # Use 3D for real cases
faces = mesh.faces

# 3. Solve eigenvalue problem (mock Helmholtz equation)
# (Replace with actual FEM setup in practice)
A = np.random.rand(100, 100)  # Mock stiffness matrix
eigenvalues, _ = eigsh(A, k=5, which="SM")
resonant_freqs = np.sqrt(np.abs(eigenvalues)) * 1000  # Scaled to Hz

print(f"First 5 resonant frequencies (Hz): {resonant_freqs}")
"""

import trimesh
import numpy as np
from scipy.sparse.linalg import eigsh

# 1. Load and repair STL
# mesh = trimesh.load("cavity.stl")
# mesh = trimesh.load("./build/LeleAllAssembly-250512-221758-ML/LeleAllAssembly.stl") # gugulele soprano
mesh = trimesh.load("./build/LeleAllAssembly-250512-222331-ML/LeleAllAssembly.stl") # gugulele guitar
assert mesh.is_watertight, "Mesh must be watertight"

# 2. Convert to FEM mesh (simplified 2D example)
vertices = mesh.vertices[:, :2]  # Use 3D for real cases
faces = mesh.faces

# 3. Solve eigenvalue problem (mock Helmholtz equation)
# (Replace with actual FEM setup in practice)
# A = np.random.rand(100, 100)  # Mock stiffness matrix
# A = 50 * np.ones((100, 100))  # Mock stiffness matrix
A = np.zeros((100, 100))  # Mock stiffness matrix
A[0, 0] = 1
A[10, 10] = 1
A[99, 99] = -1
eigenvalues, _ = eigsh(A, k=5, which="SM")
resonant_freqs = np.sqrt(np.abs(eigenvalues)) * 1000  # Scaled to Hz

print(f"First 5 resonant frequencies (Hz): {resonant_freqs}")