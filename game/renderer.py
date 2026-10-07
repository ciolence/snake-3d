"""PyOpenGL 3D renderer + camera for the snake game."""
from __future__ import annotations

from typing import Dict, Tuple

import pygame
from pygame.locals import DOUBLEBUF, OPENGL
from OpenGL.GL import (
    GL_BLEND, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST,
    GL_LINES, GL_LINEAR, GL_MODELVIEW, GL_ONE_MINUS_SRC_ALPHA, GL_PROJECTION,
    GL_QUADS, GL_RGBA, GL_SRC_ALPHA, GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER, GL_UNSIGNED_BYTE, glBegin, glBindTexture,
    glBlendFunc, glClear, glClearColor, glColor3f, glDisable, glEnable,
    glEnd, glLoadIdentity, glMatrixMode, glOrtho, glPopMatrix, glPushMatrix,
    glTexCoord2f, glTexImage2D, glTexParameteri, glVertex2f, glVertex3f,
    glViewport,
)
from OpenGL.GLU import gluLookAt, gluPerspective


def _cell_center(cell: Tuple[int, int, int], n: int) -> Tuple[float, float, float]:
    x, y, z = cell
    h = n / 2.0
    return (x - h + 0.5, y - h + 0.5, z - h + 0.5)


def _make_font(size: int, bold: bool = False):
    """Robust font loader: avoids pygame SysFont win32 registry crash."""
    pygame.font.init()
    try:
        return pygame.font.SysFont("consolas", size, bold=bold)
    except Exception:
        pass
    try:
        return pygame.font.SysFont(None, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


class Camera:
    def __init__(self, distance: float = 30.0):
        self.yaw = 45.0
        self.pitch = 28.0
        self.distance = distance

    def drag(self, dx: float, dy: float) -> None:
        self.yaw = (self.yaw + dx * 0.4) % 360.0
        self.pitch = max(5.0, min(85.0, self.pitch + dy * 0.3))

    def zoom(self, amount: float) -> None:
        self.distance = max(8.0, min(120.0, self.distance + amount))


class Renderer:
    """Owns the pygame + OpenGL window and draws one game state."""

    # Fixed GL texture name for the HUD overlay. Plain int avoids any
    # glGenTextures/glDeleteTextures wrapper-shape issues; binding an
    # unused name is legal OpenGL and we reuse it every frame.
    HUD_TEX_ID = 7

    def __init__(self, grid_size: int, width: int = 1100, height: int = 750):
        pygame.init()
        pygame.display.set_caption("3D Snake  (drag=orbit | wheel=zoom | WASD+R/F move)")
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(50.0, width / max(1, height), 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)
        self.width = width
        self.height = height
        self.camera = Camera(distance=grid_size * 2.0 + 6.0)
        self.font = _make_font(18)
        self.big_font = _make_font(44, bold=True)

    # ---------- per-frame ----------
    def draw(self, state: Dict, mode: str, paused: bool, auto_rotate: bool) -> None:
        """Draw the 3D scene. NOTE: no flip here; draw_overlay() presents."""
        import math
        if auto_rotate:
            self.camera.yaw = (self.camera.yaw + 0.15) % 360.0
        n = state["grid_size"]
        glClearColor(0.05, 0.07, 0.12, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        yaw = math.radians(self.camera.yaw)
        pitch = math.radians(self.camera.pitch)
        d = self.camera.distance
        ex = d * math.cos(pitch) * math.cos(yaw)
        ey = d * math.sin(pitch)
        ez = d * math.cos(pitch) * math.sin(yaw)
        gluLookAt(ex, ey, ez, 0, 0, 0, 0, 1, 0)

        self._draw_arena(n)
        food = state.get("food")
        if food is not None and state.get("alive"):
            self._draw_cube(food, n, (1.0, 0.25, 0.25), scale=0.62)
        body = state.get("body", [])
        for i, cell in enumerate(reversed(body)):
            t = 0.0 if len(body) <= 1 else i / max(1, len(body) - 1)
            # Tail (dark green) -> head (bright lime) gradient.
            color = (0.15 + 0.55 * t, 0.45 + 0.45 * t, 0.15)
            scale = 0.92 if t > 0.99 else 0.8
            self._draw_cube(cell, n, color, scale=scale)

    def draw_overlay(self, state: Dict, mode: str, paused: bool, fps: float, msg: str = "") -> None:
        """Draw the 2D HUD as a single OpenGL texture, then present (one flip)."""
        lines = [
            f"Mode: {mode.upper()}   Score: {state.get('score', 0)}   Length: {state.get('length', 0)}",
            f"Steps: {state.get('steps', 0)}   Head: {state.get('head')}   Food: {state.get('food')}",
            f"Dir: {state.get('direction')}   FPS: {fps:.0f}   Cam: yaw {self.camera.yaw:.0f} pitch {self.camera.pitch:.0f}",
            "Move: W/S fwd/back, A/D left/right, R/F up/down | drag orbit, wheel zoom",
            "P pause | N new game | +/- speed | ESC quit",
        ]
        hud = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 0))
        y = 8
        for line in lines:
            surf = self.font.render(line, True, (230, 235, 240))
            hud.blit(surf, (10, y))
            y += surf.get_height() + 4
        if paused:
            surf = self.big_font.render("PAUSED", True, (255, 220, 80))
            hud.blit(surf, (self.width // 2 - 110, 20))
        if msg:
            surf = self.big_font.render(msg, True, (255, 90, 90))
            hud.blit(surf, (self.width // 2 - 230, self.height // 2 - 30))

        # Orthographic 2D pass for the HUD quad (y grows downward).
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        data = pygame.image.tostring(hud, "RGBA", True)
        glBindTexture(GL_TEXTURE_2D, self.HUD_TEX_ID)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glColor3f(1.0, 1.0, 1.0)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height,
                     0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        # tostring(flipped=True): byte row 0 = visual bottom -> v=0 at y=height.
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(0, 0)
        glTexCoord2f(1, 1); glVertex2f(self.width, 0)
        glTexCoord2f(1, 0); glVertex2f(self.width, self.height)
        glTexCoord2f(0, 0); glVertex2f(0, self.height)
        glEnd()

        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        pygame.display.flip()

    # ---------- primitives ----------
    def _draw_arena(self, n: int) -> None:
        h = n / 2.0
        glColor3f(0.40, 0.55, 0.90)
        glBegin(GL_LINES)
        for i in range(n + 1):
            v = -h + i
            # floor grid (y = -h)
            glVertex3f(-h, -h, v); glVertex3f(h, -h, v)
            glVertex3f(v, -h, -h); glVertex3f(v, -h, h)
            # 12 box edges through the corners
            if i in (0, n):
                glVertex3f(v, -h, -h); glVertex3f(v, h, -h)
                glVertex3f(v, -h, h); glVertex3f(v, h, h)
                glVertex3f(-h, -h, v); glVertex3f(-h, h, v)
                glVertex3f(h, -h, v); glVertex3f(h, h, v)
                glVertex3f(-h, v, -h); glVertex3f(h, v, -h)
                glVertex3f(-h, v, h); glVertex3f(h, v, h)
        glEnd()

    def _draw_cube(self, cell: Tuple[int, int, int], n: int, color, scale: float = 0.85) -> None:
        cx, cy, cz = _cell_center(cell, n)
        s = scale / 2.0
        glColor3f(*color)
        verts = [
            (cx - s, cy - s, cz + s), (cx + s, cy - s, cz + s),
            (cx + s, cy + s, cz + s), (cx - s, cy + s, cz + s),
            (cx - s, cy - s, cz - s), (cx + s, cy - s, cz - s),
            (cx + s, cy + s, cz - s), (cx - s, cy + s, cz - s),
        ]
        faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
                 (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)]
        glBegin(GL_QUADS)
        for f in faces:
            for vi in f:
                glVertex3f(*verts[vi])
        glEnd()
        # dark edges make stacked cubes readable in full 3D
        glColor3f(0.02, 0.03, 0.05)
        glBegin(GL_LINES)
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
                 (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
        for a, b in edges:
            glVertex3f(*verts[a]); glVertex3f(*verts[b])
        glEnd()

    def close(self) -> None:
        pygame.quit()
