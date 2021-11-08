import random
import math
import arcade
import os
import numpy as np
import time

from typing import cast

STARTING_ASTEROID_COUNT = 3
SCALE = 1.0
OFFSCREEN_SPACE = 000
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Something about engineers"
LEFT_LIMIT = -OFFSCREEN_SPACE
RIGHT_LIMIT = SCREEN_WIDTH + OFFSCREEN_SPACE
BOTTOM_LIMIT = -OFFSCREEN_SPACE
TOP_LIMIT = SCREEN_HEIGHT + OFFSCREEN_SPACE
PIX_PER_M = 32


def load_anim_frames(directory):
    frames = []
    for filename in os.listdir(directory):
        if filename.endswith(".png"):
            path = os.path.join(directory, filename)
            frames.append(arcade.load_texture(path))
    return frames

class TurningSprite(arcade.Sprite):
    """ Sprite that sets its angle to the direction it is traveling in. """
    def update(self):
        """ Move the sprite """
        super().update()
        self.angle = math.degrees(math.atan2(self.change_y, self.change_x)) - 90


class ShipSprite(arcade.Sprite):
    """
    Sprite that represents our space ship.

    Derives from arcade.Sprite.
    """
    def __init__(self, filename, scale):
        """ Set up the space ship. """

        # Call the parent Sprite constructor
        super().__init__(filename, scale)

        # Info on where we are going.
        # Angle comes in automatically from the parent class.
        self.mass = 1.0
        self.thrust = np.zeros([2])
        self.velocity = np.zeros([2])
        self.vMax = np.ones([2])*8
        self.drag = 0.03
        self.respawning = 0
        self.bounce_ratio = 0.3

        # Mark that we are respawning.
        self.respawn()

    def respawn(self):
        """
        Called when we die and need to make a new ship.
        'respawning' is an invulnerability timer.
        """
        # If we are in the middle of respawning, this is non-zero.
        self.respawning = 1
        self.center_x = SCREEN_WIDTH / 2
        self.center_y = SCREEN_HEIGHT / 2

    def update(self):
        """
        Update our position and other particulars.
        """
        if self.respawning:
            self.respawning += 1
            self.alpha = 150
            if self.respawning > 150:
                self.respawning = 0
                self.alpha = 255

        dv = -self.drag * self.velocity + self.thrust / self.mass
        self.velocity += dv
        tooFast = self.velocity > self.vMax
        self.velocity[tooFast] = self.vMax[tooFast]
        tooSlow = self.velocity < -self.vMax
        self.velocity[tooSlow] = - self.vMax[tooSlow]

        self.change_x = self.velocity[0]
        self.change_y = self.velocity[1]

        self.center_x += self.change_x
        self.center_y += self.change_y

        # If the ship goes off-screen, move it to the other side of the window
        if self.left < 0:
            self.left = 0
            self.velocity[0] *= - self.bounce_ratio

        if self.right > SCREEN_WIDTH:
            self.right = SCREEN_WIDTH
            self.velocity[0] *= - self.bounce_ratio

        if self.bottom < 0:
            self.bottom = 0
            self.velocity[1] *= - self.bounce_ratio

        if self.top > SCREEN_HEIGHT:
            self.top = SCREEN_HEIGHT
            self.velocity[1] *= - self.bounce_ratio

        """ Call the parent class. """
        # super().update()


class TeapotSprite(arcade.Sprite):
    """ Sprite that represents an asteroid. """

    def __init__(self, image_file_name, scale):
        super().__init__(image_file_name, scale=scale)
        directory = os.path.dirname(image_file_name)
        self.textures = load_anim_frames(directory)
        self.cur_texture_index = 1
        self.texture = self.textures[self.cur_texture_index]
        self.size = 0
        self.max_health = 2
        self.low_health_threshold = 1
        self.health = self.max_health
        self.alive = True
        self.velocity = np.array([0,0])
        self.mass = 2
        self.f_max = 5
        self.speed_max = 4
        self.player_loc = np.array([SCREEN_WIDTH/2,SCREEN_HEIGHT/2])

    def on_update(self, delta_time = 1/60):
        """ Move the asteroid around. """

        if self.alive:
            r = self.player_loc - self.position
            force = self.f_max * r / np.linalg.norm(r)
            accel = force / self.mass
            self.velocity = self.velocity + accel*delta_time
            speed = np.linalg.norm(self.velocity)
            if speed > self.speed_max:
                self.velocity = self.velocity/ speed * self.speed_max
            self.position = self._position + self.velocity * delta_time * PIX_PER_M

        if self.center_x < LEFT_LIMIT:
            self.center_x = RIGHT_LIMIT
        if self.center_x > RIGHT_LIMIT:
            self.center_x = LEFT_LIMIT
        if self.center_y > TOP_LIMIT:
            self.center_y = BOTTOM_LIMIT
        if self.center_y < BOTTOM_LIMIT:
            self.center_y = TOP_LIMIT

    def process_hit(self):
        self.health -= 1
        if self.health <= 0:
            self.texture = self.textures[-1]
            self.alive = False
        elif self.health > 0 and self.health <= self.low_health_threshold:
            self.texture = self.textures[2]
            
            




class MyGame(arcade.Window):
    """ Main application class. """

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Set the working directory (where we expect to find files) to the same
        # directory this .py file is in. You can leave this out of your own
        # code, but it is needed to easily run the examples using "python -m"
        # as mentioned at the top of this program.
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)

        arcade.set_background_color(arcade.color.PINE_GREEN)

        self.frame_count = 0

        self.game_over = False

        # Sprite lists
        self.player_sprite_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.ship_life_list = arcade.SpriteList()

        # Set up the player
        self.score = 0
        self.player_sprite = None
        self.lives = 3

        # Set up input buffers
        self.mouse_location = np.array([0,0])
        self.mouse_pressed = {arcade.MOUSE_BUTTON_LEFT:False,
                            arcade.MOUSE_BUTTON_MIDDLE:False,
                            arcade.MOUSE_BUTTON_RIGHT:False}
        self.input_pressed = {'up':False,
                            'down':False,
                            'left':False,
                            'right':False}
        self.autoclick_period = {arcade.MOUSE_BUTTON_LEFT:0.25,
                            arcade.MOUSE_BUTTON_MIDDLE:1.0,
                            arcade.MOUSE_BUTTON_RIGHT:1.0}
        self.last_autoclick = {arcade.MOUSE_BUTTON_LEFT:0.0,
                            arcade.MOUSE_BUTTON_MIDDLE:0.0,
                            arcade.MOUSE_BUTTON_RIGHT:0.0}

        # Sounds
        self.laser_sound = arcade.load_sound(":resources:sounds/hurt5.wav")
        self.hit_sound1 = arcade.load_sound(":resources:sounds/explosion1.wav")
        self.hit_sound2 = arcade.load_sound(":resources:sounds/explosion2.wav")
        self.hit_sound3 = arcade.load_sound(":resources:sounds/hit1.wav")
        self.hit_sound4 = arcade.load_sound(":resources:sounds/hit2.wav")

    def start_new_game(self):
        """ Set up the game and initialize the variables. """

        self.frame_count = 0
        self.game_over = False

        # Sprite lists
        self.player_sprite_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.ship_life_list = arcade.SpriteList()

        # Set up the player
        self.score = 0
        self.player_sprite = ShipSprite("resources/images/wagons/basic/sprite_0.png",
                                        SCALE)
        self.player_sprite_list.append(self.player_sprite)
        self.lives = 3

        # Set up the little icons that represent the player lives.
        cur_pos = 10
        for i in range(self.lives):
            life = arcade.Sprite("resources/images/wagons/basic/sprite_0.png",
                                 SCALE)
            life.center_x = cur_pos + life.width
            life.center_y = life.height
            cur_pos += life.width
            self.ship_life_list.append(life)

        # Make the asteroids
        for i in range(STARTING_ASTEROID_COUNT):
            enemy_sprite = TeapotSprite("resources/images/enemies/teapot/sprite_1.png", SCALE)
            enemy_sprite.guid = "Teapot"

            enemy_sprite.center_y = random.randrange(BOTTOM_LIMIT, TOP_LIMIT)
            enemy_sprite.center_x = random.randrange(LEFT_LIMIT, RIGHT_LIMIT)

            enemy_sprite.change_x = random.random() * 2 - 1
            enemy_sprite.change_y = random.random() * 2 - 1

            enemy_sprite.change_angle = (random.random() - 0.5) * 2
            enemy_sprite.size = 4
            self.enemy_list.append(enemy_sprite)

    def on_draw(self):
        """
        Render the screen.
        """

        # This command has to happen before we start drawing
        arcade.start_render()

        # Draw all the sprites.
        self.enemy_list.draw(pixelated=True)
        self.ship_life_list.draw(pixelated=True)
        self.bullet_list.draw(pixelated=True)
        self.player_sprite_list.draw(pixelated=True)

        # Put the text on the screen.
        output = f"Score: {self.score}"
        arcade.draw_text(output, 10, 70, arcade.color.WHITE, 13)

        output = f"Enemy Count: {len(self.enemy_list)}"
        arcade.draw_text(output, 10, 50, arcade.color.WHITE, 13)

    def on_key_press(self, symbol, modifiers):
        """ Called whenever a key is pressed. """
        # Shoot if the player hit the space bar and we aren't respawning.
        if symbol == arcade.key.A:
            self.input_pressed['left'] = True
        elif symbol == arcade.key.D:
            self.input_pressed['right'] = True
        elif symbol == arcade.key.W:
            self.input_pressed['up'] = True
        elif symbol == arcade.key.S:
            self.input_pressed['down'] = True

    def on_key_release(self, symbol, modifiers):
        """ Called whenever a key is released. """
        if symbol == arcade.key.A:
            self.input_pressed['left'] = False
        elif symbol == arcade.key.D:
            self.input_pressed['right'] = False
        elif symbol == arcade.key.W:
            self.input_pressed['up'] = False
        elif symbol == arcade.key.S:
            self.input_pressed['down'] = False

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_location = [x, y]

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Called whenever the mouse button is clicked.
        """
        self.mouse_pressed[button] = True
        

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int):
        self.mouse_pressed[button] = False

    # def split_asteroid(self, asteroid: TeapotSprite):
    #     """ Split an asteroid into chunks. """
    #     x = asteroid.center_x
    #     y = asteroid.center_y
    #     self.score += 1

    #     if asteroid.size == 4:
    #         for i in range(3):
    #             image_no = random.randrange(2)
    #             image_list = [":resources:images/space_shooter/meteorGrey_med1.png",
    #                           ":resources:images/space_shooter/meteorGrey_med2.png"]

    #             enemy_sprite = AsteroidSprite(image_list[image_no],
    #                                           SCALE * 1.5)

    #             enemy_sprite.center_y = y
    #             enemy_sprite.center_x = x

    #             enemy_sprite.change_x = random.random() * 2.5 - 1.25
    #             enemy_sprite.change_y = random.random() * 2.5 - 1.25

    #             enemy_sprite.change_angle = (random.random() - 0.5) * 2
    #             enemy_sprite.size = 3

    #             self.asteroid_list.append(enemy_sprite)
    #             self.hit_sound1.play()

    #     elif asteroid.size == 3:
    #         for i in range(3):
    #             image_no = random.randrange(2)
    #             image_list = [":resources:images/space_shooter/meteorGrey_small1.png",
    #                           ":resources:images/space_shooter/meteorGrey_small2.png"]

    #             enemy_sprite = AsteroidSprite(image_list[image_no],
    #                                           SCALE * 1.5)

    #             enemy_sprite.center_y = y
    #             enemy_sprite.center_x = x

    #             enemy_sprite.change_x = random.random() * 3 - 1.5
    #             enemy_sprite.change_y = random.random() * 3 - 1.5

    #             enemy_sprite.change_angle = (random.random() - 0.5) * 2
    #             enemy_sprite.size = 2

    #             self.asteroid_list.append(enemy_sprite)
    #             self.hit_sound2.play()

    #     elif asteroid.size == 2:
    #         for i in range(3):
    #             image_no = random.randrange(2)
    #             image_list = [":resources:images/space_shooter/meteorGrey_tiny1.png",
    #                           ":resources:images/space_shooter/meteorGrey_tiny2.png"]

    #             enemy_sprite = AsteroidSprite(image_list[image_no],
    #                                           SCALE * 1.5)

    #             enemy_sprite.center_y = y
    #             enemy_sprite.center_x = x

    #             enemy_sprite.change_x = random.random() * 3.5 - 1.75
    #             enemy_sprite.change_y = random.random() * 3.5 - 1.75

    #             enemy_sprite.change_angle = (random.random() - 0.5) * 2
    #             enemy_sprite.size = 1

    #             self.asteroid_list.append(enemy_sprite)
    #             self.hit_sound3.play()

    #     elif asteroid.size == 1:
    #         self.hit_sound4.play()

    def on_update(self, delta_time):
        """ Move everything """

        self.process_input()

        self.frame_count += 1

        if not self.game_over:
            self.enemy_list.on_update(delta_time)
            self.bullet_list.update()
            self.player_sprite_list.update()

            for bullet in self.bullet_list:
                enemies = arcade.check_for_collision_with_list(bullet,
                                                                 self.enemy_list)

                for enemy in enemies:
                    # expected AsteroidSprite, got Sprite instead
                    # self.split_asteroid(cast(TeapotSprite, asteroid))
                    enemy.process_hit()
                    bullet.remove_from_sprite_lists()

                # Remove bullet if it goes off-screen
                size = max(bullet.width, bullet.height)
                if bullet.center_x < 0 - size:
                    bullet.remove_from_sprite_lists()
                if bullet.center_x > SCREEN_WIDTH + size:
                    bullet.remove_from_sprite_lists()
                if bullet.center_y < 0 - size:
                    bullet.remove_from_sprite_lists()
                if bullet.center_y > SCREEN_HEIGHT + size:
                    bullet.remove_from_sprite_lists()

            if not self.player_sprite.respawning:
                asteroids = arcade.check_for_collision_with_list(self.player_sprite,
                                                                 self.enemy_list)
                if len(asteroids) > 0:
                    if self.lives > 0:
                        self.lives -= 1
                        self.player_sprite.respawn()
                        # self.split_asteroid(cast(AsteroidSprite, asteroids[0]))
                        asteroids[0].remove_from_sprite_lists()
                        self.ship_life_list.pop().remove_from_sprite_lists()
                        print("Crash")
                    else:
                        self.game_over = True
                        print("Game over")

    def process_input(self):
        dx =  self.mouse_location[0] - self.player_sprite.center_x
        dy = self.mouse_location[1] - self.player_sprite.center_y

        self.player_sprite.angle = 180*math.atan2(dy, dx)/math.pi - 90

        if not self.player_sprite.respawning and self.mouse_pressed[arcade.MOUSE_BUTTON_LEFT] and \
            time.time() - self.last_autoclick[arcade.MOUSE_BUTTON_LEFT] > self.autoclick_period[arcade.MOUSE_BUTTON_LEFT]:
            
            bullet_sprite = TurningSprite("resources/images/effects/cannonball/sprite_1.png",
                                          SCALE)
            bullet_sprite.guid = "Bullet"

            bullet_speed = 30
            bullet_sprite.change_y = \
                math.cos(math.radians(self.player_sprite.angle)) * bullet_speed
            bullet_sprite.change_x = \
                -math.sin(math.radians(self.player_sprite.angle)) \
                * bullet_speed

            bullet_sprite.center_x = self.player_sprite.center_x
            bullet_sprite.center_y = self.player_sprite.center_y
            bullet_sprite.update()

            self.bullet_list.append(bullet_sprite)

            arcade.play_sound(self.laser_sound)
            self.last_autoclick[arcade.MOUSE_BUTTON_LEFT] = time.time()

        self.player_sprite.thrust[0] = 0.3 * (self.input_pressed['right'] - self.input_pressed['left'])
        self.player_sprite.thrust[1] = 0.3 * (self.input_pressed['up'] - self.input_pressed['down'])



def main():
    """ Start the game """
    window = MyGame()
    window.start_new_game()
    arcade.run()


if __name__ == "__main__":
    main()