import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import "./ChatWindow.css";
import { getAIMessage } from "../api/api";
import { marked } from "marked";

function ChatWindow({ currentChat, onUpdateTitle, onUpdateMessages }) {
  // TODO: Add message search functionality - maybe use fuse.js?
  // FIXME: Consider implementing message editing capabilities
  // NOTE: Had to refactor this component 3 times because of performance issues

  const defaultMessage = [{
    role: "assistant",
    content: "Hi, I'm your appliance parts and repair assistant. How can I help you today?",
    timestamp: new Date(),
    id: "welcome-message"
  }];

  const [messages, setMessages] = useState(currentChat?.messages || defaultMessage);
  const [userInput, setUserInput] = useState(""); //renamed from 'input' for clarity
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  // const [debugMode, setDebugMode] = useState(false); // for debugging streaming issues

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const chatContainerRef = useRef(null); // added for better scroll handling

  // Update messages when currentChat changes (with ref to prevent loops)
  const currentChatRef = useRef(currentChat);
  useEffect(() => {
    if (currentChat && currentChat.id !== currentChatRef.current?.id) {
      currentChatRef.current = currentChat;
      setMessages(currentChat.messages.length > 0 ? currentChat.messages : defaultMessage);
    }
  }, [currentChat, defaultMessage]);

  // Update parent component when messages change (debounced to prevent flickering)
  const updateTimeoutRef = useRef(null);
  useEffect(() => {
    if (currentChat && onUpdateMessages) {
      // Clear previous timeout
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
      
      // Debounce the update to prevent rapid fire updates
      updateTimeoutRef.current = setTimeout(() => {
        onUpdateMessages(currentChat.id, messages);
        
        // Auto-update chat title based on first user message
        if (messages.length > 1 && currentChat.title === "New Conversation") {
          const firstUserMessage = messages.find(msg => msg.role === "user");
          if (firstUserMessage && onUpdateTitle) {
            const title = firstUserMessage.content.slice(0, 30) + (firstUserMessage.content.length > 30 ? "..." : "");
            onUpdateTitle(currentChat.id, title);
          }
        }
      }, 50); // 50ms debounce - experimented with 100ms but felt sluggish
    }
    
    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
    };
  }, [messages, currentChat, onUpdateMessages, onUpdateTitle]);

  // Smooth scroll to bottom with better performance (debounced)
  const scrollTimeoutRef = useRef(null);
  const scrollToBottom = useCallback(() => {
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    
    scrollTimeoutRef.current = setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ 
          behavior: "smooth",
          block: "end"
        });
      }
    }, 150); // tried 100ms first but had flickering issues
  }, []);

  useEffect(() => {
      scrollToBottom();
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [messages.length, scrollToBottom]); // Only trigger on length change, not content change

  // Message sending with loading states and error handling
  // TODO: Add retry mechanism for failed requests
  const handleSend = async (inputText) => {
    const trimmedInput = inputText?.trim() || userInput.trim();
    
    if (!trimmedInput) return;

    try {
      setError(null);
      setIsLoading(true);
      
      // Add user message and loading indicator in one update to prevent flickering
      const userMessage = { 
        role: "user", 
        content: trimmedInput,
        timestamp: new Date(),
        id: `user-${Date.now()}`
      };
      
      const loadingMessage = { 
        role: "assistant", 
        content: "thinking", 
        isLoading: true,
        timestamp: new Date(),
        id: `loading-${Date.now()}`
      };
      
      // Single state update to prevent flickering
      setMessages(prevMessages => [...prevMessages, userMessage, loadingMessage]);
      setUserInput("");

      // Call API with streaming callback
      // NOTE: This streaming stuff took forever to debug!
      let currentAssistantMessage = {
        role: "assistant",
        content: "",
        timestamp: new Date(),
        id: `assistant-${Date.now()}`,
        parts: [],
        repairs: [],
        blogs: [],
        responseTime: null
      };

      // Use persistent conversation ID for context continuity
      let chatId = currentChat?.id;
      if (!chatId) {
        chatId = localStorage.getItem('current_conversation_id') || 'chat_' + Date.now();
        localStorage.setItem('current_conversation_id', chatId);
      }
      
      const aiResponse = await getAIMessage(trimmedInput, chatId, (progressData) => {
        // REAL-TIME PROGRESSIVE UPDATES!
        switch (progressData.type) {
          case 'thinking':
            // Update loading message with thinking status
            // console.log('Thinking:', progressData.content); // debug
            setMessages(prevMessages => {
              return prevMessages.map(msg => 
                msg.isLoading ? {
                  ...msg,
                  content: progressData.content,
                  isThinking: true
                } : msg
              );
            });
            break;
            
          case 'response':
            // Update with AI response as it comes in
            // This was causing duplicate messages before the fix
            currentAssistantMessage.content = progressData.content;
            setMessages(prevMessages => {
              return prevMessages.map(msg => 
                msg.isLoading ? { ...currentAssistantMessage, isLoading: false } : msg
              );
            });
            break;
            
          case 'parts':
            // Add parts as they stream in
            currentAssistantMessage.parts = progressData.content;
            setMessages(prevMessages => {
              return prevMessages.map(msg => 
                msg.id === currentAssistantMessage.id ? { ...currentAssistantMessage } : msg
              );
            });
            break;
            
          case 'repairs':
            // Add repairs as they stream in
            currentAssistantMessage.repairs = progressData.content;
            setMessages(prevMessages => {
              return prevMessages.map(msg => 
                msg.id === currentAssistantMessage.id ? { ...currentAssistantMessage } : msg
              );
            });
            break;
            
          case 'blogs':
            // Add blogs as they stream in
            currentAssistantMessage.blogs = progressData.content;
            setMessages(prevMessages => {
              return prevMessages.map(msg => 
                msg.id === currentAssistantMessage.id ? { ...currentAssistantMessage } : msg
              );
            });
            break;
            
          case 'complete':
            // Final update with response time
            currentAssistantMessage.responseTime = progressData.responseTime;
            setMessages(prevMessages => {
              return prevMessages.map(msg => 
                msg.id === currentAssistantMessage.id ? { ...currentAssistantMessage } : msg
              );
            });
            break;
        }
      });
      
      // Update conversation ID if backend returned a new one
      if (aiResponse.conversationId && aiResponse.conversationId !== chatId) {
        localStorage.setItem('current_conversation_id', aiResponse.conversationId);
      }
      
      // Fallback final update (in case streaming didn't work)
      if (aiResponse && aiResponse.content && !currentAssistantMessage.content) {
        const responseWithTimestamp = {
          ...aiResponse,
          timestamp: new Date(),
          id: `assistant-${Date.now()}`,
          responseTime: aiResponse.responseTime
        };
        
        setMessages(prevMessages => {
          return prevMessages.map(msg => 
            msg.isLoading ? responseWithTimestamp : msg
          );
        });
      }

    } catch (err) {
      console.error("Failed to get AI response:", err);
      // TODO: Implement exponential backoff for retries
      setError("Sorry, I'm having trouble connecting. Please try again.");
      
      // Replace loading message with error message
      setMessages(prevMessages => {
        return prevMessages.map(msg => 
          msg.isLoading ? {
            role: "assistant",
            content: "I apologize, but I'm experiencing technical difficulties. Please try your question again, or contact support if the problem persists.",
            timestamp: new Date(),
            id: `error-${Date.now()}`
          } : msg
        );
      });
    } finally {
      setIsLoading(false);
      // Focus back on input for better UX
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  };

  // Handle keyboard shortcuts
  // FIXME: Add support for Ctrl+Enter for new line
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading) {
        handleSend();
      }
    }
    // TODO: Add up arrow to edit last message
  };

  // Format timestamp for display - kept simple for now
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "";
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    // Could add relative time like "2 minutes ago" later
  };

  // Extract URLs from text - regex could be better but works for now
  const extractUrls = (text) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.match(urlRegex) || [];
  };

  // Extract image URLs from text
  const extractImages = (text) => {
    const imageRegex = /(https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|webp|svg))/gi;
    return text.match(imageRegex) || [];
  };

  // Function to detect if a URL might have an image
  const getImageFromUrl = (url) => {
    // Better image extraction with previews
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      // YouTube video thumbnails
      const videoIdMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
      if (videoIdMatch) {
        return `https://img.youtube.com/vi/${videoIdMatch[1]}/mqdefault.jpg`;
      }
    } else if (url.includes('partselect.com')) {
      // Use PartSelect logo for their links instead of guessing product images
      return '/partselect-minilogo.png';
    }
    return null;
  };

  // Extract a readable title from URL - works better for blog titles
  const getTitleFromUrl = (url) => {
    try {
      const urlObj = new URL(url);
      let path = urlObj.pathname;
      
      // Remove leading slash and file extensions
      path = path.replace(/^\//, '').replace(/\.[^/.]+$/, '');
      
      // Handle common URL patterns - get the most descriptive part
      if (path.includes('/')) {
        const parts = path.split('/');
        // For blog URLs, often the title is in the last segment
        const lastPart = parts[parts.length - 1];
        
        // If last part looks like a blog title (longer than 3 chars), use it
        if (lastPart && lastPart.length > 3) {
          path = lastPart;
        } else if (parts.length > 1) {
          // Otherwise use second to last part
          path = parts[parts.length - 2] || lastPart;
        }
      }
      
      // Convert hyphens/underscores to spaces and capitalize properly
      let title = path
        .replace(/[-_]/g, ' ')
        .replace(/\b\w+/g, word => {
          // Capitalize first letter of each word, keep rest lowercase
          return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        })
        .trim();
      
      // Handle common blog patterns
      if (title.includes('how to')) {
        title = title.replace(/\bhow to\b/gi, 'How To');
      }
      if (title.includes('diy')) {
        title = title.replace(/\bdiy\b/gi, 'DIY');
      }
      
      // Remove numbers at the start (often article IDs)
      title = title.replace(/^\d+\s*/, '');
      
      // Limit length but be more generous for blog titles
      return title.length > 35 ? title.substring(0, 32) + '...' : title || 'View Article';
    } catch {
      return 'View Link';
    }
  };

  // Helper function to format structured data as text within the speech bubble
  const formatStreamedDataAsText = (message) => {
    let additionalContent = "";
    
    // Add parts information
    if (message.parts && message.parts.length > 0) {
      message.parts.forEach((part, index) => {
        additionalContent += `\n\n**${part.name || 'Part'}**\n`;
        additionalContent += `Part #: ${part.part_number || 'N/A'}\n`;
        additionalContent += `Price: ${part.price || 'N/A'}\n`;
        additionalContent += `Brand: ${part.brand || 'N/A'}\n`;
        if (part.stock_status) {
          additionalContent += `Availability: ${part.stock_status}\n`;
        }
        if (part.url) {
          additionalContent += `📋 [View Part Details](${part.url})\n`;
        }
      });
    }
    
    // Add repair guides
    if (message.repairs && message.repairs.length > 0) {
      additionalContent += `\n\n**Repair Guides:**\n`;
      message.repairs.forEach((repair, index) => {
        additionalContent += `- **${repair.title}**`;
        if (repair.difficulty) {
          additionalContent += ` (Difficulty: ${repair.difficulty})`;
        }
        additionalContent += `\n`;
        if (repair.description) {
          additionalContent += `  ${repair.description}\n`;
        }
        if (repair.repair_video_url) {
          additionalContent += `  📹 [Watch Repair Video](${repair.repair_video_url})\n`;
        }
      });
    }
    
    // Add blog articles
    if (message.blogs && message.blogs.length > 0) {
      additionalContent += `\n\n**Articles that may be helpful:**\n`;
      message.blogs.forEach((blog, index) => {
        additionalContent += `- [${blog.title}](${blog.url})\n`;
      });
    }
    
    return additionalContent;
  };

  // Render rich content (images, links, etc.)
  const renderRichContent = (message) => {
    const urls = extractUrls(message.content);
    const explicitImages = extractImages(message.content);
    
    // Try to find images from regular URLs
    const potentialImages = urls
      .filter(url => !explicitImages.includes(url))
      .map(url => ({ url, imageUrl: getImageFromUrl(url) }))
      .filter(item => item.imageUrl);
    
    return (
      <>
        {/* Explicit Images */}
        {explicitImages.length > 0 && (
          <div className="message-images">
            {explicitImages.map((imageUrl, index) => (
              <div key={index} className="message-image-container">
                <img 
                  src={imageUrl} 
                  alt="Content image"
                  className="message-image"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              </div>
            ))}
          </div>
        )}
        
        {/* Link previews with potential images */}
        {urls.filter(url => !explicitImages.includes(url)).length > 0 && (
          <div className="message-links">
            {urls.filter(url => !explicitImages.includes(url)).map((url, index) => {
              const potentialImage = getImageFromUrl(url);
              const isPartSelect = url.includes('partselect.com');
              const isVideo = url.includes('youtube.com') || url.includes('youtu.be');
              const isBlog = url.includes('blog') || url.includes('article');
              
              return (
                <div key={index} className={`link-preview ${isPartSelect ? 'partselect-link' : ''}`}>
                  {/* Show image if available */}
                  {potentialImage && (
                    <div className="link-preview-image">
                      <img 
                        src={potentialImage} 
                        alt="Link preview"
                        className="preview-thumbnail"
                        onError={(e) => {
                          e.target.parentElement.style.display = 'none';
                        }}
                      />
                    </div>
                  )}
                  
                  <div className="link-preview-icon">
                    {isVideo ? '📹' : isBlog ? '📄' : isPartSelect ? '🔧' : '🔗'}
                  </div>
                  
                  <div className="link-preview-content">
                    <a href={url} target="_blank" rel="noopener noreferrer" className="link-preview-url">
                      {getTitleFromUrl(url)}
                    </a>
                    <div className="link-preview-domain">
                      {new URL(url).hostname}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </>
    );
  };

  // Message rendering with timestamps, chat bubbles, and rich content
  const renderMessage = (message, index) => {
    // Use message ID for stable keys, fallback to index
    const messageKey = message.id || `${message.role}-${index}`;
    
    if (message.isLoading) {
      return (
        <div key={messageKey} className="assistant-message-container">
          <div className="loading-message">
            Thinking<span className="loading-dots"></span>
          </div>
        </div>
      );
    }

    // Process markdown with better formatting and new tab links
    let processedContent = message.content;
    if (message.role === "assistant") {
      // Add structured data (parts, repairs, blogs) to the main content
      const structuredData = formatStreamedDataAsText(message);
      const fullContent = message.content + structuredData;
      
      processedContent = marked(fullContent, {
        breaks: true,
        gfm: true
      }).replace(/<p>|<\/p>/g, "")
       .replace(/<a href=/g, '<a target="_blank" rel="noopener noreferrer" href='); // All links open in new tab
    }

    return (
      <div key={messageKey} className={`${message.role}-message-container`}>
        <div className={`message-bubble ${message.role}-bubble`}>
          <div className={`message ${message.role}-message`}>
            {message.role === "assistant" ? (
              <div dangerouslySetInnerHTML={{__html: processedContent}} />
            ) : (
              <div>{message.content}</div>
            )}
          </div>
          
          {/* Rich content for assistant messages */}
          {message.role === "assistant" && renderRichContent(message)}
          
          <div className="message-timestamp">
            {formatTimestamp(message.timestamp)}
            {/* Show response time for assistant messages */}
            {message.role === "assistant" && message.responseTime && (
              <span className="response-time"> • {message.responseTime}s</span>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Memoize rendered messages to prevent unnecessary re-renders
  const renderedMessages = useMemo(() => {
    return messages.map(renderMessage);
  }, [messages]);

  return (
    <div className="chat-container">
      <div className="messages-container">
        {/* All messages as chat bubbles */}
        {renderedMessages}
        
        {/* Error display */}
        {error && (
          <div className="assistant-message-container">
            <div className="message assistant-message error-message">
              ⚠️ {error}
            </div>
                      </div>
                  )}
        
        <div ref={messagesEndRef} />
              </div>
      
          <div className="input-area">
        <div className="input-wrapper">
            <input
            ref={inputRef}
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
            placeholder={isLoading ? "Please wait..." : "Ask about refrigerator or dishwasher parts..."}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            maxLength={500}
          />
        </div>
        <button 
          className="send-button" 
          onClick={() => handleSend()}
          disabled={isLoading || !userInput.trim()}
        >
          {isLoading ? "..." : "Send"}
            </button>
          </div>
      </div>
);
}

export default ChatWindow;
