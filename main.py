import datetime
import sqlite3

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex

Builder.load_file('style.kv')


class DarkMode:
    """
    Class that gives the ability to every class that inherits from it to switch
    to dark mode if the `change_appearance` method has been configured properly.
    """

    def __init__(self, **kwargs):
        hour = datetime.datetime.now().hour
        if hour <= 6 or hour >= 18:
            self._night_mode = True
        else:
            self._night_mode = False

    def toggle_dark_mode(self) -> None:
        if self._night_mode is True:
            self._night_mode = False
        else:
            self._night_mode = True
        self.change_appearance()

    def change_appearance(self) -> None:
        """
        if self._night_mode (is True):
            How the object should look when using dark mode.
        else (self._night_mode is False):
            How the object should look when using light mode.
        """
        pass


class WHScreen(Screen, DarkMode):
    """ Is the main screen for the WordleHelper app. """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background = None

        self.create_background("#e9ecef")
        self.change_appearance()

    def create_background(self, color: str) -> None:
        """ Creates a background of Color `color`."""
        c = self.canvas.before
        if len(c.children) > 2:
            del c.children[3:]

        with c:
            Color(*get_color_from_hex(color))
            self.background = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)

    def update_rect(self, instance, widget) -> None:
        """Updates the size of the rectangle whenever the user changes the window size"""
        self.background.pos = instance.pos
        self.background.size = instance.size

    def toggle_dark_mode(self) -> None:
        super(WHScreen, self).toggle_dark_mode()
        self.search_for_night_mode(self.children)

    def change_appearance(self) -> None:
        if self._night_mode:
            self.create_background("#495057")
        else:
            self.create_background("#e9ecef")

    def search_for_night_mode(self, children) -> None:
        """
        Searches every widget by recursively accessing every widget's children and
        activates the dark mode for each one of them
        """

        if children:
            for child in children:
                if hasattr(child, "change_appearance") and callable(getattr(child, "change_appearance")):
                    child.toggle_dark_mode()
                self.search_for_night_mode(child.children)

    def search_words(self, input_layout, keyboard_layout, word_displayer) -> None:
        """ Checks every word and displays them if they meet the requirements."""
        known = input_layout.get_known_letters()
        existent = keyboard_layout.get_existent_letters()
        nonexistent = keyboard_layout.get_nonexistent_letters()

        def word_retriever(known_letters: list[tuple[str, int]], existent_letters: list[str],
                           nonexistent_letters: list[str]) -> str:
            """ Generator that yields each words that meets the specified requirements."""
            connection = sqlite3.connect("words.sqlite")

            def check_word(word: str) -> bool:
                """
                Checks the length, then checks the if yellow letters are in the word.
                then checks if the red letters are not in the word,
                then checks if the letters in the 5 Inputs letters are in the correct position.
                """
                if len(word) != 5:
                    return False

                for existent_letter in existent_letters:
                    if existent_letter not in word:
                        return False

                for nonexistent_letter in nonexistent_letters:
                    if nonexistent_letter in word:
                        return False

                for letter, index in known_letters:
                    if word[index] != letter:
                        return False
                return True

            for db_line in connection.execute("SELECT word from WORDS ORDER BY probability DESC"):
                if check_word(db_line[0]):
                    yield db_line[0]

        word_generator = word_retriever(known, existent, nonexistent)
        word_displayer.display_words(word_generator)


class LetterInput(TextInput):
    """ TextInput wrapper class that has a modified `insert_text` method that allows the user"""

    def insert_text(self, substring, from_undo=False):
        """
        Transforms the input into uppercase and accepts if only if it is a letter.
        The entry can only hold 1 letter at a time.
        """
        if substring.isalpha():
            self.text = ''
            substring = substring.upper()
        else:
            substring = ''

        return super().insert_text(substring, from_undo=from_undo)


class InputLayout(BoxLayout):
    """ Layout that contains five TextInputs for each letter of the word."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.window_size = Window.size
        self.entries = []

        for x in range(5):
            temp_input = LetterInput(size_hint=(None, None),
                                     multiline=False,
                                     font_size=sp(22))
            self.entries.append(temp_input)
            self.add_widget(self.entries[-1])

    @property
    def get_spacing(self):
        spacing = (Window.width - 5 * 35) // 4
        if spacing > 40:
            return 40

        return spacing

    def get_known_letters(self) -> list[tuple[str, int]]:
        """ :returns a list with the letters in the TextInputs and their position in the word."""
        known_letters = []
        for index, entry in enumerate(self.entries):
            if entry.text != '':
                known_letters.append((entry.text.lower(), index))

        return known_letters


class LetterButton(Button):
    """
    A button that represents a unique letter.
    The letter can have 3 states:
        UNKNOWN - the user does not know anything about the letter
        EXISTENT - the letter is in the word
        NONEXISTENT - the letter is not in the word
    """
    # STATES
    UNKNOWN = 'unknown'
    EXISTENT = 'existent'
    NONEXISTENT = 'nonexistent'

    states_colors = {
        UNKNOWN: (1, 1, 1, 1),
        EXISTENT: get_color_from_hex("#ffd90f"),
        NONEXISTENT: get_color_from_hex("#ff0000"),
    }

    def __init__(self, **kwargs):
        super(LetterButton, self).__init__(**kwargs)
        self.letter = self.text.lower()
        self.letter_state = LetterButton.UNKNOWN

        self.bind(on_press=self.change_state)

    def change_state(self, widget):
        """
        Changes the state of the button in this specific order:
            UNKNOWN - EXISTENT - NONEXISTENT
        """
        if self.letter_state == LetterButton.UNKNOWN:
            self.letter_state = LetterButton.EXISTENT
        elif self.letter_state == LetterButton.EXISTENT:
            self.letter_state = LetterButton.NONEXISTENT
        else:
            self.letter_state = LetterButton.UNKNOWN

        self.change_color()

    def change_color(self):
        self.background_color = LetterButton.states_colors[self.letter_state]


class LettersLayout(GridLayout):
    """ Creates a keyboard of LetterButtons to help the user type the instructions."""

    KEYBOARD = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.orientation = 'vertical'
        self.cols = 1
        # self.spacing = dp(20)
        self.letters = []
        for row in self.KEYBOARD:
            self.add_widget(BoxLayout())
            for let in row:
                self.letters.append(LetterButton(text=let.upper(),
                                                 size_hint=(None, None),
                                                 size=(Window.width / len(row), dp(40))))
                self.children[0].add_widget(self.letters[-1])

                self.children[0].size_hint_y = None
                self.children[0].bind(minimum_height=self.children[0].setter("height"))

        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))
        self.bind(width=self.update_keyboard)

    def update_keyboard(self, _, __):
        for row in self.children:
            for letter in row.children:
                letter.width = Window.width / len(row.children)

    def get_existent_letters(self) -> list[str]:
        """ :returns a list of the yellow letters (the ones that are in the word)."""
        existent_letters = []
        for letter in self.letters:
            if letter.letter_state == LetterButton.EXISTENT:
                existent_letters.append(letter.letter)

        return existent_letters

    def get_nonexistent_letters(self) -> list[str]:
        """ :returns a list of the red letters (the ones that are not in the word)."""
        nonexistent_letters = []
        for letter in self.letters:
            if letter.letter_state == LetterButton.NONEXISTENT:
                nonexistent_letters.append(letter.letter)

        return nonexistent_letters


class WordsDisplayerPanel(AnchorLayout):
    """ An AnchorLayout that adjusts its according to the window height and the words displayed."""
    def get_height(self, words_displayer_height: int, main_panel_height: int):
        if words_displayer_height > main_panel_height - 60:
            return main_panel_height - 60
        else:
            return words_displayer_height


class WordsDisplayer(GridLayout, DarkMode):
    """ A GridLayout that displays all the possible words that app found."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background = None
        self.load_starting_words()

    def create_background(self, color: str):
        c = self.canvas.before
        if len(c.children) > 2:
            del c.children[3:]

        with c:
            Color(*get_color_from_hex(color))
            self.background = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self.update_rect, pos=self.update_rect)

    def update_rect(self, instance, widget):
        self.background.pos = instance.pos
        self.background.size = instance.size

    def change_appearance(self):
        if self._night_mode:
            for label in self.children:
                label.color = (1, 1, 1)
        else:
            for label in self.children:
                label.color = (0, 0, 0)

    def load_starting_words(self):
        """ Loads the best starting words to give the user the best way to start a game."""

        self.clear_widgets()

        with open("starting_words.txt", "r", encoding='utf-8') as words_file:
            starting_words = [word.lower().strip() for word in words_file.readline().split()]

        self.add_widget(Label(text="BEST STARTING WORDS",
                              size_hint=(1, None),
                              height=dp(40),
                              bold=True))

        for word in starting_words:
            self.add_widget(Label(text=word,
                                  size_hint=(1, None),
                                  height=dp(40)))

        # Modify text color depending on Dark Mode status
        self.change_appearance()

    def display_words(self, words_list):
        """ Displays the words that the app has found."""
        self.clear_widgets()
        word_number = 0
        for word in words_list:
            word_number += 1
            self.add_widget(Label(text=word,
                                  size_hint=(1, None),
                                  height=dp(40)))
            if word_number >= 200:
                break

        self.change_appearance()


# class TextLayout(AnchorLayout):


class SettingsPopup(Popup):
    def __init__(self, entry_layout, keyboard_layout, words_displayer, **kwargs):
        super().__init__(**kwargs)
        self.el = entry_layout
        self.kl = keyboard_layout
        self.wd = words_displayer

    def reset_game(self):
        for entry in self.el.children:
            entry.text = ''
        for letter in self.kl.letters:
            letter.letter_state = LetterButton.UNKNOWN
            letter.change_color()

        self.wd.load_starting_words()

        self.dismiss()

    def get_instructions(self):
        with open("instructions.txt", "r", encoding='utf-8') as instructions_file:
            instructions = instructions_file.readlines()
        text_to_output = "".join(instructions)
        return text_to_output


class WHApplication(App):
    def build(self):
        s = WHScreen()
        return s


if __name__ == "__main__":
    WHApplication().run()
