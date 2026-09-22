// Purpose: Frontend behavior. Owner: Gaby (frontend).
//
// All game state (masked word, lives, status, wrong letters, hints) comes
// from the backend on every request. This script never stores or guesses
// the secret word - it only renders what the API just returned.

(() => {
  "use strict";

  const API_BASE = "/api";
  const HANGMAN_PARTS = [
    "part-head",
    "part-body",
    "part-arm-left",
    "part-arm-right",
    "part-leg-left",
    "part-leg-right",
  ];

  const el = {
    setupScreen: document.getElementById("setup-screen"),
    setupForm: document.getElementById("setup-form"),
    categorySelect: document.getElementById("category-select"),
    difficultySelect: document.getElementById("difficulty-select"),
    startBtn: document.getElementById("start-btn"),
    setupError: document.getElementById("setup-error"),

    gameScreen: document.getElementById("game-screen"),
    metaCategory: document.getElementById("meta-category"),
    metaDifficulty: document.getElementById("meta-difficulty"),
    livesDisplay: document.getElementById("lives-display"),
    wordDisplay: document.getElementById("word-display"),
    wrongLetters: document.getElementById("wrong-letters"),
    hintBtn: document.getElementById("hint-btn"),
    hintText: document.getElementById("hint-text"),
    keyboard: document.getElementById("keyboard"),
    gameError: document.getElementById("game-error"),

    endScreen: document.getElementById("end-screen"),
    endTitle: document.getElementById("end-title"),
    endWord: document.getElementById("end-word"),
    endComment: document.getElementById("end-comment"),
    playAgainBtn: document.getElementById("play-again-btn"),
  };

  // Mutable session state - holds only what the server just told us,
  // plus which letters have already been tried (not the word itself).
  const state = {
    gameId: null,
    maxLives: 6,
    guessedLetters: new Set(),
    status: "idle",
  };

  const CATEGORY_LABELS = {
    programming_languages: "Programming languages",
    devops_tools: "DevOps tools",
    aws_services: "AWS services",
    linux_commands: "Linux commands",
  };

  const DIFFICULTY_LABELS = {
    easy: "Easy",
    medium: "Medium",
    hard: "Hard",
  };

  async function apiPost(path, body) {
    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (networkErr) {
      throw new Error("Network error - is the backend running?");
    }

    let data = null;
    try {
      data = await response.json();
    } catch (parseErr) {
      throw new Error("The server sent an invalid response.");
    }

    if (!response.ok) {
      const message =
        (data && data.error && data.error.message) || "Something went wrong.";
      throw new Error(message);
    }

    return data;
  }

  function showScreen(name) {
    el.setupScreen.hidden = name !== "setup";
    el.gameScreen.hidden = name !== "game";
    el.endScreen.hidden = name !== "end";
  }

  function showError(target, message) {
    target.textContent = message;
    target.hidden = false;
  }

  function clearError(target) {
    target.hidden = true;
    target.textContent = "";
  }

  function buildKeyboard() {
    el.keyboard.innerHTML = "";
    for (let code = 65; code <= 90; code += 1) {
      const letter = String.fromCharCode(code);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = letter;
      btn.dataset.letter = letter;
      btn.addEventListener("click", () => handleGuess(letter));
      el.keyboard.appendChild(btn);
    }
  }

  function keyboardButton(letter) {
    return el.keyboard.querySelector(`button[data-letter="${letter}"]`);
  }

  function renderLives(livesLeft, maxLives) {
    const full = "❤️".repeat(Math.max(livesLeft, 0));
    const empty = "\u{1F5A4}".repeat(Math.max(maxLives - livesLeft, 0));
    el.livesDisplay.textContent = full + empty;
    el.livesDisplay.setAttribute(
      "aria-label",
      `${livesLeft} of ${maxLives} lives left`
    );
  }

  function renderHangman(livesLeft, maxLives) {
    const wrongCount = maxLives - livesLeft;
    const revealCount = Math.min(
      HANGMAN_PARTS.length,
      Math.ceil((wrongCount / maxLives) * HANGMAN_PARTS.length)
    );
    HANGMAN_PARTS.forEach((id, index) => {
      const node = document.getElementById(id);
      node.classList.toggle("visible", index < revealCount);
    });
  }

  function renderWrongLetters(wrongLetters) {
    el.wrongLetters.textContent = wrongLetters.length
      ? wrongLetters.join(", ")
      : "–";
  }

  function applyGuessResult(letter, data) {
    const btn = keyboardButton(letter);
    if (btn) {
      btn.disabled = true;
      btn.classList.add(data.correct ? "correct" : "wrong");
    }
    el.wordDisplay.textContent = data.masked_word;
    renderLives(data.lives_left, state.maxLives);
    renderHangman(data.lives_left, state.maxLives);
    renderWrongLetters(data.wrong_letters);
  }

  async function handleGuess(letter) {
    if (state.status !== "playing" || state.guessedLetters.has(letter)) {
      return;
    }
    state.guessedLetters.add(letter);
    const btn = keyboardButton(letter);
    if (btn) btn.disabled = true;
    clearError(el.gameError);

    try {
      const data = await apiPost("/guess", {
        game_id: state.gameId,
        letter,
      });
      applyGuessResult(letter, data);

      if (data.status === "won" || data.status === "lost") {
        state.status = data.status;
        disableKeyboard();
        el.hintBtn.disabled = true;
        setTimeout(() => endGame(data.status, data.word), 500);
      }
    } catch (err) {
      // Let the player retry this letter - re-enable its button.
      state.guessedLetters.delete(letter);
      if (btn) btn.disabled = false;
      showError(el.gameError, err.message);
    }
  }

  function disableKeyboard() {
    el.keyboard
      .querySelectorAll("button")
      .forEach((btn) => (btn.disabled = true));
  }

  async function requestHint() {
    if (state.status !== "playing") return;
    el.hintBtn.disabled = true;
    clearError(el.gameError);

    try {
      const data = await apiPost("/hint", { game_id: state.gameId });
      el.hintText.textContent = data.hint;
      el.hintText.hidden = false;
      el.hintBtn.textContent = `Get hint (${data.hints_left} left)`;
      el.hintBtn.disabled = data.hints_left <= 0 || state.status !== "playing";
    } catch (err) {
      showError(el.gameError, err.message);
      el.hintBtn.disabled = state.status !== "playing";
    }
  }

  async function endGame(status, word) {
    showScreen("end");
    el.endScreen.classList.remove("won", "lost");
    el.endScreen.classList.add(status);
    el.endTitle.textContent = status === "won" ? "You won!" : "Game over";
    el.endWord.textContent = word;
    el.endComment.textContent = "Getting AI comment…";

    try {
      const data = await apiPost("/comment", { game_id: state.gameId });
      el.endComment.textContent = data.comment;
    } catch (err) {
      el.endComment.textContent = "Couldn't load an AI comment this time.";
    }
  }

  async function startGame(category, difficulty) {
    el.startBtn.disabled = true;
    clearError(el.setupError);

    try {
      const data = await apiPost("/generate-word", { category, difficulty });

      state.gameId = data.game_id;
      state.maxLives = data.max_lives;
      state.guessedLetters = new Set();
      state.status = "playing";

      el.metaCategory.textContent = CATEGORY_LABELS[data.category] || data.category;
      el.metaDifficulty.textContent =
        DIFFICULTY_LABELS[data.difficulty] || data.difficulty;
      el.wordDisplay.textContent = Array(data.length).fill("_").join(" ");
      renderLives(data.max_lives, data.max_lives);
      renderHangman(data.max_lives, data.max_lives);
      renderWrongLetters([]);

      el.hintText.hidden = true;
      el.hintText.textContent = "";
      el.hintBtn.textContent = "Get hint";
      el.hintBtn.disabled = false;

      buildKeyboard();
      clearError(el.gameError);
      showScreen("game");
    } catch (err) {
      showError(el.setupError, err.message);
    } finally {
      el.startBtn.disabled = false;
    }
  }

  el.setupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    startGame(el.categorySelect.value, el.difficultySelect.value);
  });

  el.hintBtn.addEventListener("click", requestHint);

  el.playAgainBtn.addEventListener("click", () => {
    state.gameId = null;
    state.status = "idle";
    showScreen("setup");
  });

  document.addEventListener("keydown", (event) => {
    if (state.status !== "playing") return;
    if (!/^[a-zA-Z]$/.test(event.key)) return;
    handleGuess(event.key.toUpperCase());
  });

  showScreen("setup");
})();
