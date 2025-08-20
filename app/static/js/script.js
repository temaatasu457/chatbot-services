let messageCount = 0;
let sessionStartTime = new Date();
let sessionId = Date.now().toString();
let currentLanguage = 'ru';

const translations = {
    ru: {
        title: "Тестовый чат-бот 🤖",
        subtitle: "В данный момент сервис активно дорабатывается...",
        description: "Этот бот может подсказать любую интересующую вас информацию о Bank 🫶🏻",
        
        placeholder: "Задайте свой вопрос...",
        sendButton: "Отправить",
        thinking: "Думаю...",
        
        sessionStats: "Текущая сессия",
        messagesSent: "Сообщений отправлено:",
        sessionDuration: "Длительность сессии:",
        
        welcomeMessage: "Я - виртуальный AI ассистент. Выберите один из популярных запросов или напишите, что вас интересует 😊",
        
        errorMessage: "Извините, произошла ошибка при обработке вашего запроса."
    },
    kk: {
        title: "Тестілік чат-бот 🤖",
        subtitle: "Қазіргі уақытта қызмет белсенді түрде жетілдірілуде...",
        description: "Бұл бот Bank туралы кез келген қызықтыратын ақпаратты ұсына алады 🫶🏻",

        placeholder: "Сұрағыңызды қойыңыз...",
        sendButton: "Жіберу",
        thinking: "Ойлануда...",
        
        sessionStats: "Ағымдағы сессия",
        messagesSent: "Жіберілген хабарламалар:",
        sessionDuration: "Сессия ұзақтығы:",
        
        welcomeMessage: "Мен - AI виртуалды көмекшісімін. Танымал сұраулардың бірін таңдаңыз немесе сізді не қызықтыратынын жазыңыз 😊",
        
        errorMessage: "Кешіріңіз, сұрауыңызды өңдеу кезінде қате орын алды."
    },
    en: {
        title: "Test chatbot 🤖",
        subtitle: "The service is currently being actively refined...",
        description: "This bot can provide you with any information about Bank you're interested in 🫶🏻",
        
        placeholder: "Ask your question...",
        sendButton: "Send",
        thinking: "Thinking...",
        
        sessionStats: "Current Session",
        messagesSent: "Messages sent:",
        sessionDuration: "Session duration:",
        
        welcomeMessage: "I am AI virtual assistant. Choose one of the popular requests or write what interests you 😊",
        
        errorMessage: "Sorry, there was an error processing your request."
    }
};

function updateUIText() {
    console.log("Updating UI to language: " + currentLanguage);
    const text = translations[currentLanguage];
    
    document.querySelector('.header h1').textContent = text.title;
    document.querySelector('.header h2').textContent = text.subtitle;
    document.querySelector('.header p').textContent = text.description;
    
    document.getElementById('question').placeholder = text.placeholder;
    
    document.querySelector('.input-container button').textContent = text.sendButton;
    
    document.getElementById('thinking').textContent = text.thinking;
    
    document.querySelector('.stats h3').textContent = text.sessionStats;
    
    const msgCountLabel = document.querySelector('.stats p:nth-child(2)');
    msgCountLabel.innerHTML = text.messagesSent + ' <span id="messageCount">' + messageCount + '</span>';
    
    const sessionTimeLabel = document.querySelector('.stats p:nth-child(3)');
    sessionTimeLabel.innerHTML = text.sessionDuration + ' <span id="sessionTime">0:00</span>';
    
    console.log("UI language update completed");
}

function changeLanguage(lang) {
    console.log("Language change requested to: " + lang);
    
    currentLanguage = lang;
    
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById('lang-' + lang).classList.add('active');
    
    updateUIText();
    
    updateWelcomeMessage();
    
    console.log("Language changed to: " + lang);
}

function updateWelcomeMessage() {
    const welcomeMessageElement = document.getElementById('welcome-message');
    if (welcomeMessageElement) {
        welcomeMessageElement.innerHTML = marked.parse(translations[currentLanguage].welcomeMessage);
    } else {
        const firstAssistantMessage = document.querySelector('.assistant-message');
        if (firstAssistantMessage) {
            firstAssistantMessage.innerHTML = marked.parse(translations[currentLanguage].welcomeMessage);
        }
    }
}

function updateSessionTime() {
    const now = new Date();
    const diff = Math.floor((now - sessionStartTime) / 1000);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
    const sessionTimeElement = document.getElementById('sessionTime');
    if (sessionTimeElement) {
        sessionTimeElement.textContent = timeStr;
    }
}

function addMessage(content, isUser, isWelcome = false) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    
    if (isWelcome) {
        messageDiv.className = `message welcome-message assistant-message`;
        messageDiv.id = 'welcome-message';
    } else {
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
    }
    
    if (isUser) {
        messageDiv.textContent = content;
        messageCount++;
        const countElement = document.getElementById('messageCount'); 
        if (countElement) {
            countElement.textContent = messageCount;
        }
    } else {
        messageDiv.innerHTML = marked.parse(content);
    }
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    const questionInput = document.getElementById('question');
    const question = questionInput.value.trim();
    
    if (!question) return;
    
    console.log("Sending message with language: " + currentLanguage);
    
    addMessage(question, true);
    questionInput.value = '';
    
    const thinking = document.getElementById('thinking');
    thinking.style.display = 'block';
    
    try {
        const response = await fetch('/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                session_id: sessionId,
                language: currentLanguage
            })
        });
        
        const data = await response.json();
        
        thinking.style.display = 'none';
        addMessage(data.response, false);
        
    } catch (error) {
        thinking.style.display = 'none';
        addMessage(translations[currentLanguage].errorMessage, false);
        console.error('Error:', error);
    }
}

window.onload = function() {
    console.log("Window loaded, initializing...");
    
    setInterval(updateSessionTime, 1000);
    
    updateUIText();
    
    const chatContainer = document.getElementById('chatContainer');
    if (chatContainer) {
        chatContainer.innerHTML = '';
    }
    
    addMessage(translations[currentLanguage].welcomeMessage, false, true);
    
    console.log("Initialization complete");
};