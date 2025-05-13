#This projects presents a simple python fluid simulation.
import pygame
import random
import math

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (100, 149, 237)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
PURPLE = (128, 0, 128)

# Particle class
class Particle:
    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.radius = random.randint(2, 5)
        self.color = random.choice([WHITE, CYAN, BLUE, MAGENTA, YELLOW, ORANGE, GREEN, RED, PURPLE])
        self.opacity = random.randint(50, 255)

    def move(self):
        self.x += self.vx
        self.y += self.vy

        # Bounce off walls
        if self.x <= 0 or self.x >= WIDTH:
            self.vx *= -1
        if self.y <= 0 or self.y >= HEIGHT:
            self.vy *= -1

    def draw(self, screen):
        surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*self.color, self.opacity), (self.radius, self.radius), self.radius)
        screen.blit(surface, (self.x - self.radius, self.y - self.radius))

# Create particles with interactivity
class InteractiveParticle(Particle):
    def __init__(self):
        super().__init__()
        self.attraction_strength = random.uniform(0.05, 0.1)

    def attract(self, mx, my):
        dx = mx - self.x
        dy = my - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        if distance > 0:
            self.vx += self.attraction_strength * (dx / distance)
            self.vy += self.attraction_strength * (dy / distance)

# Create trails for particles
class ParticleTrail(InteractiveParticle):
    def __init__(self):
        super().__init__()
        self.trail = []
        self.max_trail_length = random.randint(10, 20)

    def move(self):
        super().move()
        # Add current position to trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def draw(self, screen):
        super().draw(screen)
        for i in range(1, len(self.trail)):
            start_pos = self.trail[i - 1]
            end_pos = self.trail[i]
            alpha = int((i / len(self.trail)) * 255)
            color = (*self.color[:3], alpha)
            pygame.draw.line(screen, color, start_pos, end_pos, 2)

# Create particle interactions
class ParticleInteraction(ParticleTrail):
    def __init__(self):
        super().__init__()
        self.repulsion_strength = random.uniform(0.05, 0.1)
        self.rotation_speed = random.uniform(0.01, 0.03)

    def repel(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        if 0 < distance < 50:  # Interaction range
            force = self.repulsion_strength / distance
            self.vx -= force * (dx / distance)
            self.vy -= force * (dy / distance)

    def swirl(self, mx, my):
        dx = mx - self.x
        dy = my - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        if distance > 0:
            angle = math.atan2(dy, dx) + self.rotation_speed
            self.vx += math.cos(angle) * 0.5
            self.vy += math.sin(angle) * 0.5

# Initialize screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Complex Fluid Simulation")

# Create particles
NUM_PARTICLES = 400
particles = [ParticleInteraction() for _ in range(NUM_PARTICLES)]

# Clock for controlling frame rate
clock = pygame.time.Clock()

# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Get mouse position
    mouse_x, mouse_y = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()

    # Update particles
    for i, particle in enumerate(particles):
        if mouse_pressed[0]:
            particle.attract(mouse_x, mouse_y)
        if mouse_pressed[2]:
            particle.swirl(mouse_x, mouse_y)
        for j, other_particle in enumerate(particles):
            if i != j:
                particle.repel(other_particle)
        particle.move()

    # Draw everything
    screen.fill(BLACK)
    for particle in particles:
        particle.draw(screen)

    pygame.display.flip()

    # Cap the frame rate
    clock.tick(60)

# Quit pygame
pygame.quit()
