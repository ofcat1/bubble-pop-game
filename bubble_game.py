import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.clock import Clock
from kivy.vector import Vector
from kivy.animation import Animation
from kivy.core.audio import SoundLoader
import random
import math
import os
import threading

class PowerUp:
    def __init__(self, x, y, power_type):
        self.x = x
        self.y = y
        self.power_type = power_type
        self.radius = 25
        self.life_time = 0
        self.duration = 10.0
        self.collected = False
        
        self.power_configs = {
            'slow': {
                'color': (0.5, 0.8, 1, 0.9),
                'name': 'Slow Time',
                'effect_duration': 5.0
            },
            'multi': {
                'color': (1, 0.5, 0.2, 0.9),
                'name': 'Multi Pop',
                'effect_duration': 8.0
            },
            'shield': {
                'color': (0.2, 1, 0.5, 0.9),
                'name': 'Shield',
                'effect_duration': 10.0
            },
            'double': {
                'color': (1, 1, 0.2, 0.9),
                'name': '2x Points',
                'effect_duration': 7.0
            }
        }
        
        self.config = self.power_configs[power_type]
        
    def update(self, dt):
        self.life_time += dt
        self.y += 30 * dt
        
        if self.life_time > self.duration:
            return False
        return True
    
    def contains_point(self, x, y):
        distance = math.sqrt((x - self.x)**2 + (y - self.y)**2)
        return distance <= self.radius

class ComboSystem:
    def __init__(self):
        self.combo_count = 0
        self.combo_timer = 0
        self.combo_timeout = 2.0
        self.max_combo_time = 2.0
        
    def add_pop(self):
        self.combo_count += 1
        self.combo_timer = self.combo_timeout
        return self.combo_count
    
    def update(self, dt):
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_count = 0
    
    def get_combo_multiplier(self):
        if self.combo_count < 3:
            return 1
        elif self.combo_count < 6:
            return 1.5
        elif self.combo_count < 10:
            return 2.0
        else:
            return 3.0

class TouchEffect:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.particles = []
        
        for _ in range(5):
            radius = random.uniform(3, 8)
            particle = {
                'x': x + random.uniform(-10, 10),
                'y': y + random.uniform(-10, 10),
                'vx': random.uniform(-100, 100),
                'vy': random.uniform(-100, 100),
                'radius': radius,
                'original_radius': radius,
                'lifetime': random.uniform(0.3, 0.6),
                'max_lifetime': random.uniform(0.3, 0.6),
                'color': (1, 1, 1, 0.6)
            }
            particle['max_lifetime'] = particle['lifetime']
            self.particles.append(particle)
    
    def update(self, dt):
        active_particles = []
        for particle in self.particles:
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            particle['lifetime'] -= dt
            
            particle['vy'] -= 100 * dt
            particle['vx'] *= 0.98
            particle['vy'] *= 0.98
            
            alpha = particle['lifetime'] / particle['max_lifetime']
            original_color = particle['color']
            particle['color'] = (original_color[0], original_color[1], original_color[2], alpha * original_color[3])
            
            size_factor = 0.5 + 0.5 * alpha
            particle['radius'] = particle.get('original_radius', particle['radius']) * size_factor
            
            if particle['lifetime'] > 0:
                active_particles.append(particle)
        
        self.particles = active_particles
        return len(self.particles) > 0

class Bubble:
    def __init__(self, x, y, radius, color, game_time, direction):
        self.x = x
        self.y = y
        self.original_x = x
        self.radius = radius
        self.original_radius = radius
        self.color = color
        self.original_color = color
        
        self.life_time = 0
        self.sway_amplitude = random.uniform(15, 30)
        self.sway_frequency = random.uniform(1.5, 3.0)
        self.breathe_amplitude = random.uniform(0.1, 0.3)
        self.breathe_frequency = random.uniform(2.0, 4.0)
        self.rotation_speed = random.uniform(0.5, 2.0)
        self.shimmer_phase = random.uniform(0, 2 * math.pi)
        
        # Daha yavaş hız artışı - yarıya indirildi
        speed_multiplier = 1 + (game_time / 60.0) * (1 + game_time / 180.0)  # Çok daha yavaş
        base_speed = random.uniform(50, 90)
        self.speed = base_speed * speed_multiplier
        
        self.vx = 0
        if direction == 'up':
            self.vy = self.speed
        else:
            self.vy = -self.speed
            
        self.alpha = 1.0
        self.hit_boundary = False
        
    def update(self, dt, play_area_bounds):
        self.life_time += dt
        
        self.y += self.vy * dt
        
        if self.life_time < 100:
            sway_offset = math.sin(self.life_time * self.sway_frequency) * self.sway_amplitude
            self.x = self.original_x + sway_offset
            
            breathe_factor = 1 + math.sin(self.life_time * self.breathe_frequency) * self.breathe_amplitude
            self.radius = self.original_radius * breathe_factor
        
        play_x, play_y, play_width, play_height = play_area_bounds
        
        if (self.vy > 0 and self.y + self.radius >= play_y + play_height) or \
           (self.vy < 0 and self.y - self.radius <= play_y):
            if not self.hit_boundary:
                self.hit_boundary = True
                return 'boundary_hit'
        
        if self.original_x - self.radius < play_x:
            self.original_x = play_x + self.radius
        elif self.original_x + self.radius > play_x + play_width:
            self.original_x = play_x + play_width - self.radius
                
        return True
    
    def contains_point(self, x, y):
        distance = math.sqrt((x - self.x)**2 + (y - self.y)**2)
        return distance <= self.radius

class SpecialBubble(Bubble):
    def __init__(self, x, y, radius, color, game_time, direction, bubble_type='normal'):
        super().__init__(x, y, radius, color, game_time, direction)
        self.bubble_type = bubble_type
        self.special_properties = self.get_special_properties()
        
    def get_special_properties(self):
        properties = {
            'normal': {
                'points_multiplier': 1.0,
                'special_effect': None,
                'description': 'Normal Balon'
            },
            'double_points': {
                'points_multiplier': 2.0,
                'special_effect': 'double_points',
                'description': '2x Puan Balonu'
            },
            'health': {
                'points_multiplier': 1.0,
                'special_effect': 'heal',
                'description': '+10 Can Balonu'
            },
            'time_freeze': {
                'points_multiplier': 1.5,
                'special_effect': 'freeze_time',
                'description': 'Zaman Durdurma (3s)'
            }
        }
        return properties.get(self.bubble_type, properties['normal'])
    
    def update(self, dt, play_area_bounds):
        return super().update(dt, play_area_bounds)

class GameWidget(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.bubbles = []
        self.touch_effects = []
        self.power_ups = []
        self.score = 0
        self.health = 100
        self.max_health = 100
        self.game_time = 0
        self.spawn_timer = 0
        self.spawn_interval = 1.5
        self.game_running = True
        self.game_paused = False
        self.bubbles_popped = 0
        self.bubbles_missed = 0
        
        self.combo_system = ComboSystem()
        self.power_up_timer = 0
        self.power_up_interval = 15.0
        
        self.active_powers = {
            'slow': {'active': False, 'timer': 0},
            'multi': {'active': False, 'timer': 0}, 
            'shield': {'active': False, 'timer': 0},
            'double': {'active': False, 'timer': 0}
        }
        
        self.time_frozen = False
        self.freeze_timer = 0
        self.special_bubble_info = ""
        
        self.draw_counter = 0
        self.simplified_draw = False
        self.play_area_ratio = 0.8
        
        # Ses dosyalarını yükle (sadece efektler)
        self.load_sounds()
        self.sound_enabled = self.app.sound_enabled
        
        self.game_area = Widget()
        self.add_widget(self.game_area)
        
        self.setup_ui()
        self.bind(size=self.on_size_change)
        Clock.schedule_interval(self.update, 1/30.0)

    def load_sounds(self):
        """Ses efektlerini yükle - optimize edilmiş"""
        try:
            # Balon patlatma sesi - çoklu instance için
            if os.path.exists('bubble pop.mp3'):
                # Ana ses dosyası
                self.bubble_pop_sound = SoundLoader.load('bubble pop.mp3')
                
                # Hızlı çalma için ek instance'lar oluştur
                self.bubble_sounds = []
                for i in range(5):  # 5 adet ses instance'ı
                    sound = SoundLoader.load('bubble pop.mp3')
                    if sound:
                        sound.volume = 0.8
                        self.bubble_sounds.append(sound)
                
                if self.bubble_pop_sound:
                    self.bubble_pop_sound.volume = 0.8
                    print(f"✅ Balon sesi yüklendi - {len(self.bubble_sounds)} instance")
                else:
                    print("❌ Balon patlatma sesi yüklenemedi")
                    self.bubble_pop_sound = None
                    self.bubble_sounds = []
            else:
                print("❌ bubble pop.mp3 dosyası bulunamadı")
                self.bubble_pop_sound = None
                self.bubble_sounds = []
                
            # Ses instance rotatoru
            self.current_sound_index = 0
                
        except Exception as e:
            print(f"❌ Ses dosyası yükleme hatası: {e}")
            self.bubble_pop_sound = None
            self.bubble_sounds = []

    def start_background_music(self):
        """Arkaplan müziğini başlat"""
        if self.sound_enabled and self.game_music and not self.game_music.state == 'play':
            self.game_music.play()
            
    def stop_background_music(self):
        """Arkaplan müziğini durdur"""
        if self.game_music and self.game_music.state == 'play':
            self.game_music.stop()
            
    def pause_background_music(self):
        """Arkaplan müziğini duraklat"""
        if self.game_music and self.game_music.state == 'play':
            self.game_music.stop()
            
    def resume_background_music(self):
        """Arkaplan müziğini devam ettir"""
        if self.sound_enabled and self.game_music and not self.game_music.state == 'play':
            self.game_music.play()
            
    def play_bubble_pop_sound(self):
        """Balon patlatma sesini çal"""
        if self.sound_enabled and self.bubble_pop_sound:
            try:
                # Eğer ses çalıyorsa durdur ve yeniden başlat
                if self.bubble_pop_sound.state == 'play':
                    self.bubble_pop_sound.stop()
                self.bubble_pop_sound.play()
            except Exception as e:
                print(f"Ses çalma hatası: {e}")
        
    def update_play_area(self):
        margin_x = 80
        margin_y = 140
        
        self.play_area_width = self.width - (2 * margin_x)
        self.play_area_height = self.height - (2 * margin_y)
        self.play_area_x = margin_x
        self.play_area_y = margin_y
        
    def on_size_change(self, *args):
        self.update_play_area()
        self.update_ui_positions()
        
    def setup_ui(self):
        # Score Panel
        self.score_label = Label(
            text=f'SCORE: {self.score}',
            size_hint=(None, None),
            size=(160, 40),
            font_size='18sp',
            color=(1, 1, 1, 1),
            markup=True,
            bold=True
        )
        with self.score_label.canvas.before:
            Color(0.1, 0.1, 0.3, 0.9)
            self.score_bg_rect = Rectangle(pos=self.score_label.pos, size=self.score_label.size)
            Color(0.3, 0.6, 1, 0.8)
            self.score_border = Line(rectangle=(*self.score_label.pos, *self.score_label.size), width=2)
        self.add_widget(self.score_label)
        
        # Time Panel
        self.time_label = Label(
            text=f'TIME: {int(self.game_time)}s',
            size_hint=(None, None),
            size=(140, 40),
            font_size='18sp',
            color=(1, 1, 0.3, 1),
            markup=True,
            bold=True
        )
        with self.time_label.canvas.before:
            Color(0.3, 0.2, 0.1, 0.9)
            self.time_bg_rect = Rectangle(pos=self.time_label.pos, size=self.time_label.size)
            Color(1, 0.8, 0.2, 0.8)
            self.time_border = Line(rectangle=(*self.time_label.pos, *self.time_label.size), width=2)
        self.add_widget(self.time_label)
        
        # Health Panel
        self.health_label = Label(
            text=f'HEALTH: {int(self.health)}%',
            size_hint=(None, None),
            size=(150, 40),
            font_size='18sp',
            color=(1, 0.3, 0.3, 1),
            markup=True,
            bold=True
        )
        with self.health_label.canvas.before:
            Color(0.3, 0.1, 0.1, 0.9)
            self.health_bg_rect = Rectangle(pos=self.health_label.pos, size=self.health_label.size)
            Color(1, 0.3, 0.3, 0.8)
            self.health_border = Line(rectangle=(*self.health_label.pos, *self.health_label.size), width=2)
        self.add_widget(self.health_label)
        
        # Health Progress Bar
        self.health_bar = ProgressBar(
            max=100,
            value=self.health,
            size_hint=(None, None),
            size=(150, 8)
        )
        self.add_widget(self.health_bar)
        
        # Pause Button
        self.pause_btn = Button(
            text='PAUSE',
            size_hint=(None, None),
            size=(100, 35),
            font_size='16sp',
            background_color=(0.2, 0.2, 0.5, 0.9),
            color=(1, 1, 1, 1),
            bold=True
        )
        self.pause_btn.bind(on_press=self.toggle_pause)
        self.add_widget(self.pause_btn)
        
        # Sound Button
        self.sound_btn = Button(
            text='SOUND ON',
            size_hint=(None, None),
            size=(90, 35),
            font_size='14sp',
            background_color=(0.2, 0.5, 0.2, 0.9),
            color=(1, 1, 1, 1),
            bold=True
        )
        self.sound_btn.bind(on_press=self.toggle_sound)
        self.add_widget(self.sound_btn)
        
        # Combo Display
        self.combo_label = Label(
            text='',
            size_hint=(None, None),
            size=(180, 35),
            font_size='16sp',
            color=(1, 0.8, 0.2, 1),
            markup=True,
            bold=True
        )
        with self.combo_label.canvas.before:
            Color(0.3, 0.2, 0.05, 0.9)
            self.combo_bg_rect = Rectangle(pos=self.combo_label.pos, size=self.combo_label.size)
            Color(1, 0.6, 0, 0.8)
            self.combo_border = Line(rectangle=(*self.combo_label.pos, *self.combo_label.size), width=2)
        self.add_widget(self.combo_label)
        
        # Power Status Panel
        self.power_status_label = Label(
            text='',
            size_hint=(None, None),
            size=(200, 70),
            font_size='12sp',
            color=(0.8, 1, 0.8, 1),
            markup=True,
            halign='left',
            valign='top',
            text_size=(200, None),
            bold=True
        )
        with self.power_status_label.canvas.before:
            Color(0.1, 0.3, 0.1, 0.9)
            self.power_status_bg_rect = Rectangle(pos=self.power_status_label.pos, size=self.power_status_label.size)
            Color(0.3, 1, 0.3, 0.8)
            self.power_status_border = Line(rectangle=(*self.power_status_label.pos, *self.power_status_label.size), width=2)
        self.add_widget(self.power_status_label)
        
        # Special Info Panel
        self.special_info_label = Label(
            text='',
            size_hint=(None, None),
            size=(220, 90),
            font_size='11sp',
            color=(1, 1, 0.7, 1),
            markup=True,
            halign='left',
            valign='top',
            text_size=(220, None),
            bold=True
        )
        with self.special_info_label.canvas.before:
            Color(0.2, 0.2, 0.05, 0.9)
            self.special_info_bg_rect = Rectangle(pos=self.special_info_label.pos, size=self.special_info_label.size)
            Color(1, 1, 0.3, 0.8)
            self.special_info_border = Line(rectangle=(*self.special_info_label.pos, *self.special_info_label.size), width=2)
        self.add_widget(self.special_info_label)
        
        # Speed Display
        self.speed_label = Label(
            text='SPEED: x1.0',
            size_hint=(None, None),
            size=(120, 30),
            font_size='14sp',
            color=(0.5, 1, 0.5, 1),
            markup=True,
            bold=True
        )
        with self.speed_label.canvas.before:
            Color(0.1, 0.2, 0.1, 0.9)
            self.speed_bg_rect = Rectangle(pos=self.speed_label.pos, size=self.speed_label.size)
            Color(0.3, 1, 0.3, 0.8)
            self.speed_border = Line(rectangle=(*self.speed_label.pos, *self.speed_label.size), width=2)
        self.add_widget(self.speed_label)
        
        # Statistics Panel
        self.stats_label = Label(
            text=f'POPPED: {self.bubbles_popped} | MISSED: {self.bubbles_missed}',
            size_hint=(None, None),
            size=(220, 30),
            font_size='12sp',
            color=(0.8, 0.8, 1, 1),
            markup=True,
            bold=True
        )
        with self.stats_label.canvas.before:
            Color(0.1, 0.1, 0.2, 0.9)
            self.stats_bg_rect = Rectangle(pos=self.stats_label.pos, size=self.stats_label.size)
            Color(0.5, 0.5, 1, 0.8)
            self.stats_border = Line(rectangle=(*self.stats_label.pos, *self.stats_label.size), width=2)
        self.add_widget(self.stats_label)
        
        self.update_play_area()
        self.update_ui_positions()
        
    def update_ui_positions(self):
        margin = 15
        
        # Top section
        self.score_label.pos = (margin, self.height - 50)
        self.time_label.pos = (self.width/2 - 70, self.height - 50)
        self.health_label.pos = (self.width - 280, self.height - 50)
        self.health_bar.pos = (self.width - 280, self.height - 65)
        self.pause_btn.pos = (self.width - 110, self.height - 50)
        self.sound_btn.pos = (self.width - 110, self.height - 90)
        self.combo_label.pos = (self.width/2 - 90, self.height - 90)
        
        # Bottom section
        bottom_y = margin
        self.power_status_label.pos = (margin, bottom_y + 30)
        self.speed_label.pos = (margin, bottom_y)
        self.stats_label.pos = (self.width/2 - 110, bottom_y)
        self.special_info_label.pos = (self.width - 230, bottom_y)
        
        # Update background rectangles and borders
        self.update_ui_graphics()
        
    def update_ui_graphics(self):
        ui_elements = [
            (self.score_label, self.score_bg_rect, self.score_border, (0.1, 0.1, 0.3, 0.9), (0.3, 0.6, 1, 0.8)),
            (self.time_label, self.time_bg_rect, self.time_border, (0.3, 0.2, 0.1, 0.9), (1, 0.8, 0.2, 0.8)),
            (self.health_label, self.health_bg_rect, self.health_border, (0.3, 0.1, 0.1, 0.9), (1, 0.3, 0.3, 0.8)),
            (self.combo_label, self.combo_bg_rect, self.combo_border, (0.3, 0.2, 0.05, 0.9), (1, 0.6, 0, 0.8)),
            (self.power_status_label, self.power_status_bg_rect, self.power_status_border, (0.1, 0.3, 0.1, 0.9), (0.3, 1, 0.3, 0.8)),
            (self.special_info_label, self.special_info_bg_rect, self.special_info_border, (0.2, 0.2, 0.05, 0.9), (1, 1, 0.3, 0.8)),
            (self.speed_label, self.speed_bg_rect, self.speed_border, (0.1, 0.2, 0.1, 0.9), (0.3, 1, 0.3, 0.8)),
            (self.stats_label, self.stats_bg_rect, self.stats_border, (0.1, 0.1, 0.2, 0.9), (0.5, 0.5, 1, 0.8))
        ]
        
        for label, bg_rect, border, bg_color, border_color in ui_elements:
            bg_rect.pos = label.pos
            bg_rect.size = label.size
            border.rectangle = (*label.pos, *label.size)
        
    def toggle_pause(self, instance=None):
        if self.game_paused:
            self.resume_game()
        else:
            self.pause_game()
            
    def pause_game(self):
        if not self.game_running or self.game_paused:
            return
            
        self.game_paused = True
        self.pause_btn.text = 'RESUME'
        self.pause_btn.background_color = (0.2, 0.8, 0.2, 0.9)
        
    def resume_game(self):
        if not self.game_paused:
            return
            
        self.game_paused = False
        self.pause_btn.text = 'PAUSE'
        self.pause_btn.background_color = (0.2, 0.2, 0.5, 0.9)
        
    def toggle_sound(self, instance=None):
        """Ses açma/kapama - app seviyesinde yönet"""
        self.app.toggle_music()
        
    def spawn_bubble(self):
        if not self.game_running or self.game_paused:
            return
            
        spawn_side = random.choice(['bottom', 'top'])
        
        safe_margin = 80
        x = random.uniform(
            self.play_area_x + safe_margin, 
            self.play_area_x + self.play_area_width - safe_margin
        )
        
        time_factor = self.game_time / 120.0
        min_radius = max(12, 30 - time_factor * 12)
        max_radius = max(20, 50 - time_factor * 20)
        radius = random.uniform(min_radius, max_radius)
        
        radius_margin = radius + 10
        
        if spawn_side == 'bottom':
            y = self.play_area_y + radius_margin
            direction = 'up'
        else:
            y = self.play_area_y + self.play_area_height - radius_margin
            direction = 'down'
            
        colors = [
            (1, 0.2, 0.2, 0.85), (0.2, 1, 0.2, 0.85), (0.2, 0.2, 1, 0.85),
            (1, 1, 0.2, 0.85), (1, 0.2, 1, 0.85), (0.2, 1, 1, 0.85),
            (1, 0.5, 0, 0.85), (0.8, 0.4, 1, 0.85), (1, 0.6, 0.8, 0.85),
            (0.4, 0.8, 0.4, 0.85), (0.6, 0.3, 0.8, 0.85), (1, 0.8, 0.3, 0.85),
            (0.3, 0.7, 0.9, 0.85), (0.9, 0.5, 0.3, 0.85), (0.5, 1, 0.7, 0.85), (1, 0.4, 0.6, 0.85)
        ]
        color = random.choice(colors)
        
        bubble_type = 'normal'
        special_chance = random.random()
        
        if special_chance < 0.05:
            bubble_type = 'double_points'
            color = (1, 1, 0.2, 0.95)
        elif special_chance < 0.08:
            bubble_type = 'health'
            color = (0.2, 1, 0.2, 0.95)
        elif special_chance < 0.10:
            bubble_type = 'time_freeze'
            color = (0.5, 0.5, 1, 0.95)
        
        if bubble_type != 'normal':
            bubble = SpecialBubble(x, y, radius, color, self.game_time, direction, bubble_type)
        else:
            bubble = Bubble(x, y, radius, color, self.game_time, direction)
            
        self.bubbles.append(bubble)
        
    def spawn_power_up(self):
        if not self.game_running or self.game_paused:
            return
            
        power_types = ['slow', 'multi', 'shield', 'double']
        power_type = random.choice(power_types)
        
        margin = 100
        x = random.uniform(
            self.play_area_x + margin, 
            self.play_area_x + self.play_area_width - margin
        )
        y = self.play_area_y + self.play_area_height * 0.4
        
        power_up = PowerUp(x, y, power_type)
        self.power_ups.append(power_up)
        
    def activate_power_up(self, power_type):
        if power_type in self.active_powers:
            config = PowerUp(0, 0, power_type).config
            self.active_powers[power_type]['active'] = True
            self.active_powers[power_type]['timer'] = config['effect_duration']

    def draw_game(self):
        self.game_area.canvas.clear()
        
        with self.game_area.canvas:
            if self.game_paused:
                Color(0.05, 0.05, 0.15, 0.8)
            elif self.active_powers['slow']['active']:
                Color(0.05, 0.05, 0.25, 0.5)
            else:
                Color(0.05, 0.05, 0.15, 0.3)
            Rectangle(pos=(self.play_area_x, self.play_area_y), size=(self.play_area_width, self.play_area_height))
            
            Color(0.3, 0.6, 1, 0.8)
            Line(rectangle=(self.play_area_x-2, self.play_area_y-2, self.play_area_width+4, self.play_area_height+4), width=4)
            Color(0.6, 0.8, 1, 0.4)
            Line(rectangle=(self.play_area_x-6, self.play_area_y-6, self.play_area_width+12, self.play_area_height+12), width=2)
            
            if self.game_paused:
                Color(0, 0, 0.2, 0.6)
                Rectangle(pos=(0, 0), size=(self.width, self.height))
                
                pause_x = self.width/2 - 100
                pause_y = self.height/2 - 25
                Color(0.2, 0.2, 0.5, 0.9)
                Rectangle(pos=(pause_x-10, pause_y-10), size=(220, 70))
                Color(0.5, 0.5, 1, 0.8)
                Line(rectangle=(pause_x-10, pause_y-10, 220, 70), width=3)
            
            for power_up in self.power_ups:
                glow_size = power_up.radius * 2.5
                glow_intensity = 0.3 + 0.2 * math.sin(power_up.life_time * 4.0)
                Color(*power_up.config['color'][:3], glow_intensity)
                Ellipse(
                    pos=(power_up.x - glow_size, power_up.y - glow_size),
                    size=(glow_size * 2, glow_size * 2)
                )
                
                Color(*power_up.config['color'])
                Ellipse(
                    pos=(power_up.x - power_up.radius, power_up.y - power_up.radius),
                    size=(power_up.radius * 2, power_up.radius * 2)
                )
                
                ring_size = power_up.radius * (1.5 + 0.3 * math.sin(power_up.life_time * 6.0))
                Color(*power_up.config['color'][:3], 0.8)
                Line(circle=(power_up.x, power_up.y, ring_size), width=4)
            
            for i, bubble in enumerate(self.bubbles):
                detailed_draw = (i % 3 == 0) or (len(self.bubbles) < 10)
                is_special = hasattr(bubble, 'bubble_type') and bubble.bubble_type != 'normal'
                
                if is_special:
                    glow_radius = bubble.radius * 2.2
                    glow_alpha = 0.4 * (0.7 + 0.3 * math.sin(bubble.life_time * 5.0))
                    
                    if bubble.bubble_type == 'double_points':
                        Color(1, 1, 0, glow_alpha)
                    elif bubble.bubble_type == 'health':
                        Color(0, 1, 0, glow_alpha)
                    elif bubble.bubble_type == 'time_freeze':
                        Color(0.5, 0.5, 1, glow_alpha)
                    
                    Ellipse(
                        pos=(bubble.x - glow_radius, bubble.y - glow_radius),
                        size=(glow_radius * 2, glow_radius * 2)
                    )
                
                alpha_multiplier = 0.5 if self.game_paused else 1.0
                
                Color(*bubble.color[:3], bubble.alpha * bubble.color[3] * alpha_multiplier)
                Ellipse(
                    pos=(bubble.x - bubble.radius, bubble.y - bubble.radius),
                    size=(bubble.radius * 2, bubble.radius * 2)
                )
                
                if detailed_draw:
                    Color(*bubble.color[:3], bubble.alpha * bubble.color[3] * 0.6 * alpha_multiplier)
                    Ellipse(
                        pos=(bubble.x - bubble.radius * 0.8, bubble.y - bubble.radius * 0.8),
                        size=(bubble.radius * 1.6, bubble.radius * 1.6)
                    )
                    
                    Color(1, 1, 1, bubble.alpha * 0.7 * alpha_multiplier)
                    highlight_size = bubble.radius * 0.5
                    highlight_x = bubble.x - bubble.radius * 0.3
                    highlight_y = bubble.y + bubble.radius * 0.2
                    Ellipse(
                        pos=(highlight_x - highlight_size/2, highlight_y - highlight_size/2),
                        size=(highlight_size, highlight_size)
                    )
            
            for effect in self.touch_effects:
                for particle in effect.particles:
                    glow_radius = particle['radius'] * 1.5
                    Color(*particle['color'][:3], particle['color'][3] * 0.3)
                    Ellipse(
                        pos=(particle['x'] - glow_radius, particle['y'] - glow_radius),
                        size=(glow_radius * 2, glow_radius * 2)
                    )
                    
                    Color(*particle['color'])
                    Ellipse(
                        pos=(particle['x'] - particle['radius'], particle['y'] - particle['radius']),
                        size=(particle['radius'] * 2, particle['radius'] * 2)
                    )
    
    def update(self, dt):
        if not self.game_running or self.game_paused:
            self.draw_game()
            self.update_labels()
            return
        
        self.draw_counter += 1
        
        if self.time_frozen:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.time_frozen = False
            else:
                self.draw_game()
                self.update_labels()
                return
                
        self.game_time += dt
        self.combo_system.update(dt)
        
        self.power_up_timer += dt
        if self.power_up_timer >= self.power_up_interval:
            self.spawn_power_up()
            self.power_up_timer = 0
            self.power_up_interval = random.uniform(12.0, 18.0)
        
        for power_type, power_data in self.active_powers.items():
            if power_data['active']:
                power_data['timer'] -= dt
                if power_data['timer'] <= 0:
                    power_data['active'] = False
        
        self.spawn_timer += dt
        
        time_factor = self.game_time / 90.0
        spawn_reduction = time_factor * (1 + time_factor * 0.25)
        current_spawn_interval = max(0.4, self.spawn_interval - spawn_reduction)
        
        if self.active_powers['slow']['active']:
            current_spawn_interval *= 2.0
        
        if self.spawn_timer >= current_spawn_interval:
            self.spawn_bubble()
            self.spawn_timer = 0
        
        play_area_bounds = (self.play_area_x, self.play_area_y, self.play_area_width, self.play_area_height)
        new_bubbles = []
        for bubble in self.bubbles:
            result = bubble.update(dt, play_area_bounds)
            if result == 'boundary_hit':
                if not self.active_powers['shield']['active']:
                    damage = self.calculate_damage(bubble.radius)
                    self.health -= damage
                    self.bubbles_missed += 1
                
                self.create_boundary_hit_effect(bubble.x, bubble.y, bubble.radius)
                
                if self.health <= 0:
                    self.health = 0
                    self.game_over()
            elif result:
                new_bubbles.append(bubble)
        
        self.bubbles = new_bubbles
        
        self.power_ups = [power_up for power_up in self.power_ups if power_up.update(dt)]
        
        if len(self.touch_effects) > 20:
            self.touch_effects = self.touch_effects[-20:]
        self.touch_effects = [effect for effect in self.touch_effects if effect.update(dt)]
        
        if len(self.bubbles) > 15:
            if not self.active_powers['shield']['active']:
                self.health -= 2 * dt
        
        if self.health <= 0:
            self.health = 0
            self.game_over()
        
        self.draw_game()
        self.update_labels()
    
    def calculate_damage(self, radius):
        base_damage = 8
        size_multiplier = (radius / 25.0)
        return base_damage * size_multiplier
    
    def create_boundary_hit_effect(self, x, y, radius):
        particle_count = min(int(radius / 4) + 2, 8)
        for _ in range(particle_count):
            effect = TouchEffect(x, y)
            for particle in effect.particles:
                particle['color'] = (1, 0.2, 0.2, 0.9)
                particle['vx'] = random.uniform(-250, 250)
                particle['vy'] = random.uniform(-250, 250)
                particle['lifetime'] = random.uniform(0.4, 0.8)
                particle['max_lifetime'] = particle['lifetime']
            self.touch_effects.append(effect)
                    
    def update_labels(self):
        if self.draw_counter % 3 == 0:
            self.score_label.text = f'[b]SCORE: {self.score}[/b]'
            
            if self.game_paused:
                self.time_label.text = f'[b]PAUSED - {int(self.game_time)}s[/b]'
            else:
                self.time_label.text = f'[b]TIME: {int(self.game_time)}s[/b]'
                
            self.health_label.text = f'[b]HEALTH: {int(self.health)}%[/b]'
            self.health_bar.value = self.health
            
            if self.combo_system.combo_count >= 3:
                multiplier = self.combo_system.get_combo_multiplier()
                self.combo_label.text = f'[b]{self.combo_system.combo_count}x COMBO! (x{multiplier:.1f})[/b]'
            else:
                self.combo_label.text = ''
            
            active_powers_text = ''
            for power_type, power_data in self.active_powers.items():
                if power_data['active']:
                    config = PowerUp(0, 0, power_type).config
                    time_left = int(power_data['timer'])
                    active_powers_text += f"{config['name']}: {time_left}s\n"
            
            self.power_status_label.text = f'[b]{active_powers_text}[/b]'
            
            speed_mult = 1 + (self.game_time / 60.0) * (1 + self.game_time / 180.0)
            if self.active_powers['slow']['active']:
                speed_mult *= 0.5
            self.speed_label.text = f'[b]SPEED: x{speed_mult:.1f}[/b]'
            
            self.stats_label.text = f'[b]POPPED: {self.bubbles_popped} | MISSED: {self.bubbles_missed}[/b]'
        
        if self.draw_counter % 10 == 0:
            special_info = self.get_special_bubble_info()
            self.special_info_label.text = f'[b]{special_info}[/b]' if special_info else ''
    
    def get_special_bubble_info(self):
        special_bubbles = []
        for bubble in self.bubbles:
            if hasattr(bubble, 'bubble_type') and bubble.bubble_type != 'normal':
                special_bubbles.append(bubble)
        
        if not special_bubbles:
            return "SPECIAL BUBBLES:\nYellow: 2x Points\nGreen: +10 Health\nBlue: Time Freeze"
        
        info_text = "ACTIVE SPECIALS:\n"
        special_types = {}
        
        for bubble in special_bubbles:
            if bubble.bubble_type not in special_types:
                special_types[bubble.bubble_type] = 0
            special_types[bubble.bubble_type] += 1
        
        descriptions = {
            'double_points': 'Yellow: 2x Points',
            'health': 'Green: +10 Health',
            'time_freeze': 'Blue: Time Freeze'
        }
        
        for bubble_type, count in special_types.items():
            description = descriptions.get(bubble_type, bubble_type)
            info_text += f"{description} ({count})\n"
        
        return info_text.strip()
        
    def on_touch_down(self, touch):
        if (self.pause_btn.x <= touch.x <= self.pause_btn.x + self.pause_btn.width and
            self.pause_btn.y <= touch.y <= self.pause_btn.y + self.pause_btn.height):
            self.toggle_pause()
            return True
            
        if (self.sound_btn.x <= touch.x <= self.sound_btn.x + self.sound_btn.width and
            self.sound_btn.y <= touch.y <= self.sound_btn.y + self.sound_btn.height):
            self.toggle_sound()
            return True
            
        if not self.game_running or self.game_paused:
            return False
        
        if (touch.x < self.play_area_x or touch.x > self.play_area_x + self.play_area_width or
            touch.y < self.play_area_y or touch.y > self.play_area_y + self.play_area_height):
            return False
        
        self.touch_effects.append(TouchEffect(touch.x, touch.y))
        
        # Hızlı balon kontrolü ve anında ses çalma
        bubble_touched = False
        for bubble in self.bubbles:
            if bubble.contains_point(touch.x, touch.y):
                bubble_touched = True
                # SES ANINDA ÇAL - daha fazla kontrol beklemeden
                self.play_bubble_pop_sound()
                break
        
        power_up_collected = False
        for power_up in self.power_ups[:]:
            if power_up.contains_point(touch.x, touch.y):
                self.power_ups.remove(power_up)
                self.activate_power_up(power_up.power_type)
                self.create_power_up_collect_effect(power_up.x, power_up.y, power_up.config)
                power_up_collected = True
                break
        
        bubble_hit = False
        bubbles_to_pop = []
        
        for current_bubble in self.bubbles[:]:
            if current_bubble.contains_point(touch.x, touch.y):
                bubbles_to_pop.append(current_bubble)
                
                if self.active_powers['multi']['active']:
                    for other_bubble in self.bubbles:
                        if other_bubble != current_bubble:
                            distance = math.sqrt((current_bubble.x - other_bubble.x)**2 + (current_bubble.y - other_bubble.y)**2)
                            if distance <= 80:
                                if other_bubble not in bubbles_to_pop:
                                    bubbles_to_pop.append(other_bubble)
                break
        
        for bubble_to_pop in bubbles_to_pop:
            if bubble_to_pop in self.bubbles:
                self.bubbles.remove(bubble_to_pop)
                self.bubbles_popped += 1
                bubble_hit = True
                
                combo_count = self.combo_system.add_pop()
                combo_multiplier = self.combo_system.get_combo_multiplier()
                
                base_points = 10
                size_bonus = int((bubble_to_pop.radius / 25.0) * 15)
                
                special_multiplier = 1.0
                if hasattr(bubble_to_pop, 'bubble_type'):
                    special_multiplier = bubble_to_pop.get_special_properties()['points_multiplier']
                    
                    if bubble_to_pop.bubble_type == 'time_freeze':
                        self.time_frozen = True
                        self.freeze_timer = 3.0
                    elif bubble_to_pop.bubble_type == 'health':
                        self.health = min(100, self.health + 10)
                
                total_points = int((base_points + size_bonus) * combo_multiplier * special_multiplier)
                
                if self.active_powers['double']['active']:
                    total_points *= 2
                
                self.score += total_points
                
                if hasattr(bubble_to_pop, 'bubble_type') and bubble_to_pop.bubble_type != 'normal':
                    self.create_special_pop_effect(bubble_to_pop.x, bubble_to_pop.y, bubble_to_pop.radius, bubble_to_pop.bubble_type)
                else:
                    self.create_pop_effect(bubble_to_pop.x, bubble_to_pop.y, bubble_to_pop.radius)
        
        if not bubble_hit and not power_up_collected:
            if not self.active_powers['shield']['active']:
                self.health -= 2
            extra_effect = TouchEffect(touch.x, touch.y)
            for particle in extra_effect.particles:
                particle['color'] = (0.5, 0.8, 1, 0.4)
            self.touch_effects.append(extra_effect)
                
        return True
    
    def create_pop_effect(self, x, y, radius):
        particle_count = min(int(radius / 4) + 4, 10)
        
        for _ in range(particle_count):
            particle_x = x + random.uniform(-radius*0.3, radius*0.3)
            particle_y = y + random.uniform(-radius*0.3, radius*0.3)
            
            effect = TouchEffect(particle_x, particle_y)
            for p in effect.particles[:3]:
                p_radius = random.uniform(2, radius*0.3)
                p['radius'] = p_radius
                p['original_radius'] = p_radius
                p['lifetime'] = random.uniform(0.4, 0.8)
                p['max_lifetime'] = p['lifetime']
                
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 250)
                p['vx'] = math.cos(angle) * speed
                p['vy'] = math.sin(angle) * speed
                
                colors = [
                    (1, 0.3, 0.3, 0.9), (1, 0.7, 0.3, 0.9), (1, 1, 0.3, 0.9),
                    (0.3, 1, 0.3, 0.9), (0.3, 0.7, 1, 0.9)
                ]
                p['color'] = random.choice(colors)
            self.touch_effects.append(effect)
    
    def create_power_up_collect_effect(self, x, y, config):
        for _ in range(10):
            effect = TouchEffect(x, y)
            for p in effect.particles[:2]:
                p_radius = random.uniform(5, 12)
                p['radius'] = p_radius
                p['original_radius'] = p_radius
                p['lifetime'] = random.uniform(0.8, 1.5)
                p['max_lifetime'] = p['lifetime']
                
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 200)
                p['vx'] = math.cos(angle) * speed
                p['vy'] = math.sin(angle) * speed
                p['color'] = config['color']
            self.touch_effects.append(effect)
    
    def create_special_pop_effect(self, x, y, radius, bubble_type):
        if bubble_type == 'double_points':
            particle_count = 12
        elif bubble_type == 'health':
            particle_count = 15
        elif bubble_type == 'time_freeze':
            particle_count = 18
        else:
            particle_count = 8
            
        for _ in range(particle_count):
            effect = TouchEffect(x, y)
            for p in effect.particles[:2]:
                p_radius = random.uniform(3, 12)
                p['radius'] = p_radius
                p['original_radius'] = p_radius
                p['lifetime'] = random.uniform(0.6, 1.2)
                p['max_lifetime'] = p['lifetime']
                
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(150, 350)
                p['vx'] = math.cos(angle) * speed
                p['vy'] = math.sin(angle) * speed
                
                if bubble_type == 'double_points':
                    p['color'] = (1, 1, 0.2, 1.0)
                elif bubble_type == 'health':
                    p['color'] = (0.2, 1, 0.2, 1.0)
                elif bubble_type == 'time_freeze':
                    ice_colors = [(0.3, 0.8, 1, 1.0), (0.5, 0.5, 1, 1.0)]
                    p['color'] = random.choice(ice_colors)
                    
            self.touch_effects.append(effect)
    
    def game_over(self):
        self.game_running = False
        Clock.unschedule(self.update)
        
        accuracy = 0
        if self.bubbles_popped + self.bubbles_missed > 0:
            accuracy = (self.bubbles_popped / (self.bubbles_popped + self.bubbles_missed)) * 100
            
        self.app.game_over(self.score, int(self.game_time), self.bubbles_popped, self.bubbles_missed, accuracy)

class MenuWidget(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        
        with self.canvas.before:
            Color(0.05, 0.1, 0.2, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.1, 0.15, 0.3, 0.8)
            Rectangle(pos=self.pos, size=(self.size[0], self.size[1]/2))
        
        self.bind(size=self.update_bg)
        
        main_box = BoxLayout(
            orientation='vertical',
            spacing=40,
            padding=[60, 100, 60, 100],
            size_hint=(0.85, 0.9),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        title = Label(
            text='BUBBLE POP',
            font_size='48sp',
            size_hint_y=0.2,
            color=(0.3, 0.9, 1, 1),
            bold=True,
            markup=True
        )
        main_box.add_widget(title)
        
        subtitle = Label(
            text='Ultimate Bubble Popping Experience',
            font_size='18sp',
            size_hint_y=0.08,
            color=(0.8, 0.8, 1, 1),
            italic=True
        )
        main_box.add_widget(subtitle)
        
        instructions = Label(
            text='Tap bubbles to pop them!\nSpeed increases over time\nBubbles hitting borders reduce health\nPlay only within the game area!\nLarger bubbles give more points\nPop quickly for combos!\nCollect special bubbles and power-ups!\nYou can pause anytime!',
            font_size='15sp',
            size_hint_y=0.3,
            halign='center',
            color=(1, 1, 1, 0.9),
            text_size=(None, None),
            markup=True
        )
        main_box.add_widget(instructions)
        
        if hasattr(app, 'high_score') and app.high_score > 0:
            high_score_label = Label(
                text=f'HIGH SCORE: {app.high_score}',
                font_size='22sp',
                size_hint_y=0.1,
                color=(1, 1, 0, 1),
                bold=True,
                markup=True
            )
            main_box.add_widget(high_score_label)
        
        button_box = BoxLayout(orientation='vertical', spacing=20, size_hint_y=0.32)
        
        # Sound Toggle Button - menüde
        sound_btn = Button(
            text='SOUND ON' if app.sound_enabled else 'SOUND OFF',
            font_size='16sp',
            size_hint_y=0.25,
            background_color=(0.2, 0.5, 0.2, 1) if app.sound_enabled else (0.5, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        sound_btn.bind(on_press=lambda x: app.toggle_music())
        button_box.add_widget(sound_btn)
        
        play_btn = Button(
            text='START GAME',
            font_size='24sp',
            size_hint_y=0.5,
            background_color=(0.1, 0.6, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        play_btn.bind(on_press=self.start_game)
        button_box.add_widget(play_btn)
        
        scores_btn = Button(
            text='SCORE TABLE',
            font_size='18sp',
            size_hint_y=0.25,
            background_color=(0.2, 0.2, 0.6, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        scores_btn.bind(on_press=self.show_scores)
        button_box.add_widget(scores_btn)
        
        main_box.add_widget(button_box)
        self.add_widget(main_box)
        
    def update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.05, 0.1, 0.2, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.1, 0.15, 0.3, 0.8)
            Rectangle(pos=self.pos, size=(self.size[0], self.size[1]/2))
        
    def start_game(self, instance):
        self.app.start_game()
        
    def show_scores(self, instance):
        self.app.show_score_table()

class ScoreTableWidget(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        
        with self.canvas.before:
            Color(0.05, 0.15, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.1, 0.25, 0.1, 0.8)
            Rectangle(pos=self.pos, size=(self.size[0], self.size[1]/2))
        
        self.bind(size=self.update_bg)
        
        main_box = BoxLayout(
            orientation='vertical',
            spacing=30,
            padding=[60, 100, 60, 100],
            size_hint=(0.9, 0.8),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        title = Label(
            text='SCORE TABLE',
            font_size='38sp',
            size_hint_y=0.2,
            color=(0.3, 1, 0.3, 1),
            bold=True,
            markup=True
        )
        main_box.add_widget(title)
        
        scores_info = BoxLayout(orientation='vertical', spacing=20, size_hint_y=0.6)
        
        if hasattr(app, 'high_score') and app.high_score > 0:
            high_score_label = Label(
                text=f'HIGH SCORE: {app.high_score}',
                font_size='28sp',
                color=(1, 1, 0, 1),
                bold=True,
                markup=True
            )
            scores_info.add_widget(high_score_label)
            
        if hasattr(app, 'last_score') and app.last_score > 0:
            last_score_label = Label(
                text=f'LAST SCORE: {app.last_score}',
                font_size='22sp',
                color=(0.8, 0.8, 1, 1),
                bold=True,
                markup=True
            )
            scores_info.add_widget(last_score_label)
            
        if hasattr(app, 'best_time') and app.best_time > 0:
            time_label = Label(
                text=f'BEST TIME: {app.best_time}s',
                font_size='20sp',
                color=(1, 0.8, 0.5, 1),
                bold=True,
                markup=True
            )
            scores_info.add_widget(time_label)
            
        if hasattr(app, 'best_accuracy') and app.best_accuracy > 0:
            accuracy_label = Label(
                text=f'BEST ACCURACY: {app.best_accuracy:.1f}%',
                font_size='20sp',
                color=(0.5, 1, 0.8, 1),
                bold=True,
                markup=True
            )
            scores_info.add_widget(accuracy_label)
        
        main_box.add_widget(scores_info)
        
        # Sound control in score table
        sound_btn = Button(
            text='SOUND ON' if app.sound_enabled else 'SOUND OFF',
            font_size='16sp',
            size_hint_y=0.1,
            background_color=(0.2, 0.5, 0.2, 1) if app.sound_enabled else (0.5, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        sound_btn.bind(on_press=lambda x: app.toggle_music())
        main_box.add_widget(sound_btn)
        
        back_btn = Button(
            text='BACK TO MENU',
            font_size='20sp',
            size_hint_y=0.1,
            background_color=(0.6, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        back_btn.bind(on_press=self.back_to_menu)
        main_box.add_widget(back_btn)
        
        self.add_widget(main_box)
        
    def update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.05, 0.15, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.1, 0.25, 0.1, 0.8)
            Rectangle(pos=self.pos, size=(self.size[0], self.size[1]/2))
            
    def back_to_menu(self, instance):
        self.app.show_menu()

class GameOverWidget(FloatLayout):
    def __init__(self, app, score, game_time, bubbles_popped, bubbles_escaped, accuracy, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        
        with self.canvas.before:
            Color(0.2, 0.05, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.3, 0.1, 0.1, 0.8)
            Rectangle(pos=self.pos, size=(self.size[0], self.size[1]/2))
        
        self.bind(size=self.update_bg)
        
        main_box = BoxLayout(
            orientation='vertical',
            spacing=30,
            padding=[60, 80, 60, 80],
            size_hint=(0.9, 0.9),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        
        title = Label(
            text='GAME OVER',
            font_size='42sp',
            size_hint_y=0.15,
            color=(1, 0.3, 0.3, 1),
            bold=True,
            markup=True
        )
        main_box.add_widget(title)
        
        score_info = BoxLayout(orientation='vertical', spacing=15, size_hint_y=0.5)
        
        final_score = Label(
            text=f'FINAL SCORE: {score}',
            font_size='32sp',
            color=(1, 1, 0, 1),
            bold=True,
            markup=True
        )
        score_info.add_widget(final_score)
        
        stats_text = f'Game Time: {game_time}s\nBubbles Popped: {bubbles_popped}\nBubbles Missed: {bubbles_escaped}\nAccuracy: {accuracy:.1f}%'
        
        stats_label = Label(
            text=stats_text,
            font_size='18sp',
            color=(0.9, 0.9, 0.9, 1),
            halign='center',
            markup=True,
            bold=True
        )
        score_info.add_widget(stats_label)
        
        if hasattr(app, 'high_score'):
            if score > app.high_score:
                new_record_label = Label(
                    text='NEW RECORD!',
                    font_size='28sp',
                    color=(0, 1, 0, 1),
                    bold=True,
                    markup=True
                )
                score_info.add_widget(new_record_label)
        
        main_box.add_widget(score_info)
        
        # Sound control button
        sound_btn = Button(
            text='SOUND ON' if app.sound_enabled else 'SOUND OFF',
            font_size='16sp',
            size_hint_y=0.1,
            background_color=(0.2, 0.5, 0.2, 1) if app.sound_enabled else (0.5, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        sound_btn.bind(on_press=lambda x: app.toggle_music())
        main_box.add_widget(sound_btn)
        
        button_box = BoxLayout(orientation='vertical', spacing=20, size_hint_y=0.25)
        
        play_again_btn = Button(
            text='PLAY AGAIN',
            font_size='20sp',
            size_hint_y=0.5,
            background_color=(0.2, 0.6, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        play_again_btn.bind(on_press=self.play_again)
        button_box.add_widget(play_again_btn)
        
        menu_btn = Button(
            text='MAIN MENU',
            font_size='18sp',
            size_hint_y=0.25,
            background_color=(0.2, 0.2, 0.6, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        menu_btn.bind(on_press=self.back_to_menu)
        button_box.add_widget(menu_btn)
        
        quit_btn = Button(
            text='QUIT',
            font_size='18sp',
            size_hint_y=0.25,
            background_color=(0.6, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        quit_btn.bind(on_press=self.quit_game)
        button_box.add_widget(quit_btn)
        
        main_box.add_widget(button_box)
        self.add_widget(main_box)
        
    def update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.2, 0.05, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)
            Color(0.3, 0.1, 0.1, 0.8)
            Rectangle(pos=self.pos, size=(self.size[0], self.size[1]/2))
            
    def play_again(self, instance):
        self.app.start_game()
        
    def back_to_menu(self, instance):
        self.app.show_menu()
        
    def quit_game(self, instance):
        self.app.stop()

class BubblePopApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.high_score = 0
        self.last_score = 0
        self.best_time = 0
        self.best_accuracy = 0
        self.current_widget = None
        
        # Müzik sistemi - app seviyesinde
        self.game_music = None
        self.sound_enabled = True
        self.load_music()
        
    def load_music(self):
        """Müziği yükle"""
        try:
            if os.path.exists('game music.mp3'):
                self.game_music = SoundLoader.load('game music.mp3')
                if self.game_music:
                    self.game_music.volume = 0.4
                    self.game_music.loop = True
                    print("Müzik yüklendi (app seviyesi)")
                else:
                    print("Müzik yüklenemedi")
            else:
                print("game music.mp3 dosyası bulunamadı")
        except Exception as e:
            print(f"Müzik yükleme hatası: {e}")
    
    def start_music(self):
        """Müziği başlat"""
        if self.sound_enabled and self.game_music and self.game_music.state != 'play':
            self.game_music.play()
    
    def stop_music(self):
        """Müziği durdur"""
        if self.game_music and self.game_music.state == 'play':
            self.game_music.stop()
    
    def toggle_music(self):
        """Müziği aç/kapat"""
        self.sound_enabled = not self.sound_enabled
        if self.sound_enabled:
            self.start_music()
        else:
            self.stop_music()
        
        # Aktif game widget'a ses durumunu bildir
        if hasattr(self.current_widget, 'sound_enabled'):
            self.current_widget.sound_enabled = self.sound_enabled
            if hasattr(self.current_widget, 'sound_btn'):
                self.current_widget.sound_btn.text = 'SOUND ON' if self.sound_enabled else 'SOUND OFF'
                self.current_widget.sound_btn.background_color = (0.2, 0.5, 0.2, 0.9) if self.sound_enabled else (0.5, 0.2, 0.2, 0.9)
        
    def build(self):
        self.title = "bubble_game"
        self.show_menu()
        # Müziği başlat
        self.start_music()
        return self.current_widget
        
    def show_menu(self):
        if self.current_widget:
            self.root.clear_widgets()
        self.current_widget = MenuWidget(self)
        if hasattr(self, 'root') and self.root:
            self.root.add_widget(self.current_widget)
        else:
            self.root = self.current_widget
        # Müziği devam ettir
        self.start_music()
            
    def start_game(self):
        if self.current_widget:
            self.root.clear_widgets()
        self.current_widget = GameWidget(self)
        self.root.add_widget(self.current_widget)
        # Müziği devam ettir
        self.start_music()
        
    def show_score_table(self):
        if self.current_widget:
            self.root.clear_widgets()
        self.current_widget = ScoreTableWidget(self)
        self.root.add_widget(self.current_widget)
        # Müziği devam ettir
        self.start_music()
        
    def game_over(self, score, game_time, bubbles_popped, bubbles_escaped, accuracy):
        self.last_score = score
        if score > self.high_score:
            self.high_score = score
            
        if game_time > self.best_time:
            self.best_time = game_time
            
        if accuracy > self.best_accuracy:
            self.best_accuracy = accuracy
        
        if self.current_widget:
            self.root.clear_widgets()
        self.current_widget = GameOverWidget(
            self, score, game_time, bubbles_popped, bubbles_escaped, accuracy
        )
        self.root.add_widget(self.current_widget)

if __name__ == '__main__':
    BubblePopApp().run()