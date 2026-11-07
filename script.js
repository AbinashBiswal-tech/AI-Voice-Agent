
const API_URL = "";

const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const speakBtn = document.getElementById("speakBtn");
const chatArea = document.getElementById("chatArea");
const statusText = document.getElementById("statusText");
const connectionStatus = document.getElementById("connectionStatus");
const aiOrb = document.getElementById("aiOrb");

const historyBtn = document.getElementById("historyBtn");
const historyPanel = document.getElementById("historyPanel");
const closeHistory = document.getElementById("closeHistory");
const historyList = document.getElementById("historyList");

let conversations = JSON.parse(
    localStorage.getItem("voiceAgentHistory") || "[]"
);

// Add a message to the chat window
function addMessage(role, text) {
    const message = document.createElement("div");
    message.className =
        role === "user"
            ? "message user-message"
            : "message assistant-message";

    const label = document.createElement("strong");
    label.textContent = role === "user" ? "You: " : "AI Agent: ";

    message.appendChild(label);
    message.appendChild(document.createTextNode(text));

    chatArea.appendChild(message);
    chatArea.scrollTop = chatArea.scrollHeight;
}

// Save messages in browser history
function saveConversation(role, text) {
    conversations.push({
        role: role,
        content: text,
        time: new Date().toLocaleString()
    });

    localStorage.setItem(
        "voiceAgentHistory",
        JSON.stringify(conversations)
    );
}

// Speak AI response
function speakResponse(text) {
    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-IN";
    speech.rate = 1;

    window.speechSynthesis.speak(speech);
}

// Send message to Gemini backend
async function sendMessage() {
    const message = messageInput.value.trim();

    if (!message) return;

    addMessage("user", message);
    saveConversation("user", message);

    messageInput.value = "";

    statusText.textContent = "● THINKING · Gemini is responding...";
    aiOrb.style.animationDuration = "0.6s";
    sendBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Gemini request failed");
        }

        const reply = data.reply || "No response received.";

        addMessage("assistant", reply);
        saveConversation("assistant", reply);

        speakResponse(reply);

        statusText.textContent = "● READY · Speak or Type Command";
        connectionStatus.textContent = "● Gemini Connected";

    } catch (error) {
        console.error("Gemini Error:", error);

        addMessage(
            "assistant",
            "Connection error: " + error.message
        );

        statusText.textContent = "● CONNECTION ERROR";
        connectionStatus.textContent = "● Connection Error";
    } finally {
        sendBtn.disabled = false;
        aiOrb.style.animationDuration = "2.5s";
        messageInput.focus();
    }
}

// Send button
sendBtn.addEventListener("click", sendMessage);

// Enter key
messageInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

// Microphone input using browser speech recognition
speakBtn.addEventListener("click", function() {
    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert(
            "Speech recognition is not supported in this browser. Please use Google Chrome."
        );
        return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    statusText.textContent = "● LISTENING · Speak now...";
    speakBtn.disabled = true;

    recognition.onresult = function(event) {
        const transcript =
            event.results[0][0].transcript;

        messageInput.value = transcript;
        sendMessage();
    };

    recognition.onerror = function(event) {
        statusText.textContent = "● Microphone error: " + event.error;
    };

    recognition.onend = function() {
        speakBtn.disabled = false;

        if (!sendBtn.disabled) {
            statusText.textContent =
                "● READY · Speak or Type Command";
        }
    };

    recognition.start();
});

// Open chat history
historyBtn.addEventListener("click", function() {
    historyPanel.classList.remove("hidden");
    showHistory();
});

// Close chat history
closeHistory.addEventListener("click", function() {
    historyPanel.classList.add("hidden");
});

// Display saved messages
function showHistory() {
    historyList.replaceChildren();

    if (conversations.length === 0) {
        const empty = document.createElement("p");
        empty.textContent = "No saved conversations yet.";
        historyList.appendChild(empty);
        return;
    }

    conversations.forEach(function(item) {
        const entry = document.createElement("div");
        entry.className = "message assistant-message";

        const heading = document.createElement("strong");
        heading.textContent =
            item.role === "user" ? "You: " : "AI Agent: ";

        const content = document.createElement("p");
        content.textContent = item.content;

        const time = document.createElement("small");
        time.textContent = item.time;

        entry.append(heading, content, time);
        historyList.appendChild(entry);
    });
}

// Check backend connection
async function checkConnection() {
    try {
        const response = await fetch(`${API_URL}/`);

        if (!response.ok) {
            throw new Error("Backend unavailable");
        }

        connectionStatus.textContent = "● Gemini Backend Online";

    } catch (error) {
        connectionStatus.textContent = "● Backend Offline";
        console.error(error);
    }
}

checkConnection();
