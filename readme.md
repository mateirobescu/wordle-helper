# WordleHelperV3

## Project Overview

**WordleHelperV3** is a simple, cross-platform application built with **Python** and the **Kivy** framework, designed to assist players in solving the popular Wordle puzzle.

The application acts as an **intelligent word filter**: users input the clues received from the Wordle game—such as the exact position of letters (GREEN), letters that exist but are misplaced (YELLOW), and letters that are absent (RED)—using a dedicated input row and an interactive, three-state keyboard.

By querying its internal dictionary (stored in `words.sqlite`), the application instantly filters and displays a list of all remaining valid words, helping players choose their next best guess. It also suggests a list of optimized starting words to maximize early success.