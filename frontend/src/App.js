import React, { useState, useEffect } from "react";
import "./App.css";
import ChatWindow from "./components/ChatWindow";
// import { saveToLocalStorage, loadFromLocalStorage } from "./utils/storage"; // TODO: implement this

function App() {
  // TODO: Add user session persistence to localStorage - started but not finished
  // FIXME: Consider implementing chat export functionality
  // NOTE: Sidebar toggle was added after initial implementation
  
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  // const [isDarkMode, setIsDarkMode] = useState(false); // for future theme support

  // Initialize with first chat - this runs on every app load
  useEffect(() => {
    // console.log('Initializing chat history, current length:', chatHistory.length); // debug
    if (chatHistory.length === 0) {
      const firstChat = {
        id: Date.now().toString(),
        title: "New Conversation", 
        createdAt: new Date(),
        messages: []
      };
      setChatHistory([firstChat]);
      setCurrentChatId(firstChat.id);
    }
  }, [chatHistory.length]);

  const createNewChat = () => {
    // TODO: Generate better unique IDs, maybe use uuid?
    const newChat = {
      id: Date.now().toString(),
      title: "New Conversation", 
      createdAt: new Date(),
      messages: []
    };
    setChatHistory(prevChats => [newChat, ...prevChats]); // renamed for clarity
    setCurrentChatId(newChat.id);
  };

  const selectChat = (chatId) => {
    // console.log('Selecting chat:', chatId); // debug
    setCurrentChatId(chatId);
    // TODO: Add loading state while switching chats
  };

  const updateChatTitle = (chatId, newTitle) => {
    // This gets called automatically when user sends first message
    setChatHistory(prevChats => prevChats.map(chat => 
      chat.id === chatId ? { ...chat, title: newTitle } : chat
    ));
  };

  const updateChatMessages = (chatId, newMessages) => {
    // This gets called frequently during conversations
    setChatHistory(prevChats => prevChats.map(chat => 
      chat.id === chatId ? { ...chat, messages: newMessages } : chat
    ));
  };

  const currentChat = chatHistory.find(chat => chat.id === currentChatId);
  // const totalMessages = chatHistory.reduce((sum, chat) => sum + chat.messages.length, 0); // for stats later

  return (
    <div className="App">
      <div className="heading">
        <div className="heading-logo">
          <img src="/partselect-minilogo.png" alt="PartSelect" />
          <div className="heading-content">
            <div className="heading-title">
              Instalily Parts Finder
            </div>
            <div className="heading-subtitle">
              Appliance Parts Assistant
            </div>
          </div>
        </div>
        <div className="heading-badge">
          AI Powered
        </div>
      </div>
      
      <div className="app-layout">
        {/* Chat History Sidebar */}
        <div className={`chat-sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <div className="sidebar-header">
            <h3>Chat History</h3>
            <button className="new-chat-btn" onClick={createNewChat}>
              + New Chat
            </button>
            {/* <button onClick={() => setSidebarOpen(!sidebarOpen)}>Toggle</button> */}
          </div>
          <div className="chat-list">
            {chatHistory.map((chat, index) => ( // added index for debugging
              <div 
                key={chat.id}
                className={`chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => selectChat(chat.id)}
                // title={`${chat.messages.length} messages`} // tooltip for message count
              >
                <div className="chat-item-title">{chat.title}</div>
                <div className="chat-item-date">
                  {chat.createdAt.toLocaleDateString()}
                </div>
                {/* <div className="message-count">{chat.messages.length}</div> */}
              </div>
            ))}
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="chat-main">
          {currentChat ? (
            <ChatWindow 
              currentChat={currentChat}
              onUpdateTitle={updateChatTitle}
              onUpdateMessages={updateChatMessages}
            />
          ) : (
            <div className="no-chat-selected">Select a chat to start</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
