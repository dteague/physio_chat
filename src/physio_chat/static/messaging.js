//
// 1. API CONFIGURATION
//

// Use "/chat" when FastAPI serves the website.
// If the frontend runs on another port, use
// "http://localhost:8000/chat" instead.
const API_URL = "/chat";

// Adapt these functions to your Pydantic schemas.
const apiFormat = {
    chatId: chat => chat.id,
    chatTitle: chat => chat.title ?? `Chat ${chat.id}`,

    chatList: data => data,
    chatMessages: data => data.messages,

    messageBody: text => ({ query: text }),

    messageRole: message => message.role,
    messageContent: message => message.content
};

//
// 2. API FUNCTIONS
//

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers
        }
    });

    if (!response.ok) {
        throw new Error(
            `API error: ${response.status} ${response.statusText}`
        );
    }

    if (response.status === 204) return null;

    return response.json();
}

async function apiListChats() {
    return apiRequest("");
}

async function apiCreateChat() {
    return apiRequest("", {
        method: "POST"
    });
}

async function apiGetChat(chatId) {
    return apiRequest(`/${chatId}`);
}

async function apiGetChatStatus(chatId) {
    return apiRequest(`/${chatId}/status`);
}

async function apiSendMessage(chatId, text) {
    return apiRequest(`/${chatId}/message`, {
        method: "POST",
        body: JSON.stringify(apiFormat.messageBody(text))
    });
}

async function apiDeleteChat(chatId) {
    return apiRequest(`/${chatId}`, {
        method: "DELETE"
    });
}


//
// 3. APPLICATION STATE
//

let conversations = [];
let activeChatId = null;
let messages = [];

// Prevent outdated requests from replacing newer views.
let loadVersion = 0;

// Track ongoing sends by chat ID.
const pendingChats = new Set();

const form = document.getElementById("chat-form");
const input = document.getElementById("message");
const chatWindow = document.getElementById("chat-messages");
const titleElement = document.getElementById("chat-title");
const conversationList =
    document.getElementById("conversation-list");
const newChatButton = document.getElementById("new-chat");


//
// 4. RENDERING FUNCTIONS
//

function renderSidebar() {
    conversationList.replaceChildren();

    for (const conversation of conversations) {
        const id = apiFormat.chatId(conversation);

        // Container for conversation and delete button
        const container = document.createElement("div");
        container.className = "conversation-row";

        const button = document.createElement("button");
        button.className = "conversation-item";
        button.textContent = apiFormat.chatTitle(conversation);

        if (id === activeChatId) {
            button.classList.add("active");
        }

        button.addEventListener("click", () => {
            selectChat(id);
        });

        // Delete button
        const deleteButton = document.createElement("button");
        deleteButton.textContent = "×";
        deleteButton.className = "delete-chat";
        deleteButton.title = "Delete conversation";
        deleteButton.setAttribute(
            "aria-label", "Delete conversation"
        );

        deleteButton.addEventListener("click", () => {
            deleteChat(id);
        });

        container.appendChild(button);
        container.appendChild(deleteButton);
        conversationList.appendChild(container);
    }
}

function renderMessages() {
    chatWindow.replaceChildren();

    if (activeChatId == null) {
        chatWindow.textContent = "Creating conversation...";
        return;
    }

    for (const message of messages) {
        const div = document.createElement("div");

        const rawRole = apiFormat.messageRole(message);
        const role = rawRole === "user" ? "user" : "ai";

        div.className = `message ${role}`;
        div.textContent = apiFormat.messageContent(message);

        chatWindow.appendChild(div);
    }

    if (pendingChats.has(activeChatId)) {
        const thinking = document.createElement("div");
        thinking.className = "message ai";
        thinking.textContent = "Thinking...";
        chatWindow.appendChild(thinking);
    }

    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function updateInputState() {
    const disabled = activeChatId === null ||
        pendingChats.has(activeChatId);

    input.disabled = disabled;
    form.querySelector("button").disabled = disabled;
}

function showError(error) {
    console.error(error);
    const div = document.createElement("div");
    div.className = "message ai";
    div.textContent = `Error: ${error.message}`;
    chatWindow.appendChild(div);
}


//
// 5. CONVERSATION MANAGEMENT
//

async function refreshChatList() {
    const data = await apiListChats();
    conversations = apiFormat.chatList(data);
    renderSidebar();
}

async function selectChat(chatId) {
    if (chatId === null || chatId === undefined) {
        return;
    }

    activeChatId = chatId;

    // Each selection invalidates previous loading requests.
    const version = ++loadVersion;

    messages = [];
    titleElement.textContent = "Loading...";

    renderSidebar();
    renderMessages();
    updateInputState();

    try {
        const data = await apiGetChat(chatId);
        if (data.status === "initializing") {
            titleElement.textContent = "Initializing chat...";
            input.disabled = true;
        } else if (data.status === "failed") {
            titleElement.textContent = "Initialization failed";
            input.disabled = true;
        } else {
            titleElement.textContent = data.title ?? "New Chat";
            input.disabled = false;
        }

        // Ignore a result if the user switched chats.
        if (version !== loadVersion) return;

        messages = apiFormat.chatMessages(data);
        titleElement.textContent = apiFormat.chatTitle(data);
        renderMessages();

        // In case chat is in middle of process, rerender after ready
        waitForChat(chatId);

    } catch (error) {
        if (version === loadVersion) {
            showError(error);
        }
    }

    updateInputState();
}

const POLL_INTERVAL = 1000; // One second

const sleep = ms =>
    new Promise(resolve => setTimeout(resolve, ms));

async function waitForChat(chatId) {
    while (true) {
        // Stop if the user switched chats.
        if (activeChatId !== chatId) return;

        const status = await apiGetChatStatus(chatId);

        // Check again after the asynchronous request.
        if (activeChatId !== chatId) return;

        if (status === "ready") {
            // Rerender text (now that it's ready)
            const data = await apiGetChat(chatId);
            messages = data.messages;
            renderMessages();
            return;
        }

        if (status === "failed") {
            throw new Error("AI generation failed");
        }

        await sleep(POLL_INTERVAL);
    }

}

async function createChat() {
    newChatButton.disabled = true;

    try {
        const newChat = await apiCreateChat();

        const chatId = newChat.id

        await refreshChatList();
        await selectChat(chatId);

    } catch (error) {
        showError(error);
    } finally {
        newChatButton.disabled = false;
    }
}

async function deleteChat(chatId) {
    if (pendingChats.has(chatId)) {
        alert("Please wait for the AI response first.");
        return;
    }

    if (!confirm("Delete this conversation?")) return;

    try {
        await apiDeleteChat(chatId);

        const wasActive = activeChatId === chatId;

        await refreshChatList();

        if (wasActive) {
            // Invalidate previous loads.
            ++loadVersion;
            activeChatId = null;
            messages = [];

            if (conversations.length > 0) {
                await selectChat(
                    apiFormat.chatId(conversations[0])
                );
            } else {
                titleElement.textContent = "New Chat";
                renderSidebar();
                renderMessages();
                updateInputState();
            }
        }
    } catch (error) {
        showError(error);
    }
}


//
// 6. SENDING MESSAGES
//

form.addEventListener("submit", async event => {
    event.preventDefault();

    const text = input.value.trim();
    const chatId = activeChatId;

    if (!text || chatId === null ||
        pendingChats.has(chatId)) {
        return;
    }

    // Mark this specific conversation as busy.
    pendingChats.add(chatId);

    // Optimistically display the user's message.
    messages.push({
        role: "user",
        content: text
    });

    input.value = "";
    renderMessages();
    updateInputState();

    try {
        await apiSendMessage(chatId, text);
        await waitForChat(chatId);

        // The backend may have updated the title.
        await refreshChatList();

    } catch (error) {
        if (activeChatId === chatId) {
            showError(error);
        }
    } finally {
        pendingChats.delete(chatId);

        if (activeChatId === chatId) {
            renderMessages();
            updateInputState();
        }
    }
});


//
// 7. EVENT HANDLERS AND INITIALIZATION
//

newChatButton.addEventListener("click", createChat);

async function initialize() {
    try {
        await refreshChatList();

        if (conversations.length > 0) {
            await selectChat(
                apiFormat.chatId(conversations[0])
            );
        } else {
            titleElement.textContent = "New Chat";
            updateInputState();
        }
    } catch (error) {
        showError(error);
    }
}

initialize();
