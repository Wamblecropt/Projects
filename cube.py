#This project is definitely one of my most intriguing ones. It presents a rotating cube with a nice black background.

import pygame
import sys
from pygame.locals import *
import numpy as np
# Initialize Pygame
pygame.init()
# Set up the window
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Rotating Cube')
# Set up the colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
# Define cube vertices
vertices = [
    [-1, -1, -1],
    [-1, -1, 1],
    [-1, 1, -1],
    [-1, 1, 1],
    [1, -1, -1],
    [1, -1, 1],
    [1, 1, -1],
    [1, 1, 1]
]
# Define cube edges
edges = [
    (0, 1),
    (1, 3),
    (3, 2),
    (2, 0),
    (4, 5),
    (5, 7),
    (7, 6),
    (6, 4),
    (0, 4),
    (1, 5),
    (3, 7),
    (2, 6)
]
# Set up rotation parameters
angle_x = 0
angle_y = 0
angle_z = 0
# Main loop
while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
    # Clear the screen
    window.fill(BLACK)
    # Define rotation matrices
    rotation_x = np.array([
        [1, 0, 0],
        [0, np.cos(angle_x), -np.sin(angle_x)],
        [0, np.sin(angle_x), np.cos(angle_x)]
    ])
    rotation_y = np.array([
        [np.cos(angle_y), 0, np.sin(angle_y)],
        [0, 1, 0],
        [-np.sin(angle_y), 0, np.cos(angle_y)]
    ])
    rotation_z = np.array([
        [np.cos(angle_z), -np.sin(angle_z), 0],
        [np.sin(angle_z), np.cos(angle_z), 0],
        [0, 0, 1]
    ])
    # Apply rotation matrices to vertices
    rotated_vertices = []
    for vertex in vertices:
        rotated_vertex = vertex.copy()
        rotated_vertex = np.dot(rotation_x, rotated_vertex)
        rotated_vertex = np.dot(rotation_y, rotated_vertex)
        rotated_vertex = np.dot(rotation_z, rotated_vertex)
        rotated_vertices.append(rotated_vertex)
    # Project vertices onto 2D screen
    projected_vertices = []
    for vertex in rotated_vertices:
        z = 1 / (vertex[2] + 3)
        projected_vertex = [vertex[0] * z, vertex[1] * z]
        projected_vertices.append(projected_vertex)
    # Draw edges
    for edge in edges:
        start_pos = projected_vertices[edge[0]]
        end_pos = projected_vertices[edge[1]]
        pygame.draw.line(window, WHITE, (start_pos[0] * 100 + WINDOW_WIDTH // 2, start_pos[1] * 100 + WINDOW_HEIGHT // 2),
                         (end_pos[0] * 100 + WINDOW_WIDTH // 2, end_pos[1] * 100 + WINDOW_HEIGHT // 2))
    # Update rotation angles
    angle_x += 0.01
    angle_y += 0.01
    angle_z += 0.01
    # Update the display
    pygame.display.update()
    # Limit frame rate
    pygame.time.Clock().tick(60)
