import { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([
    { 
      text: "Hello! I am your AI Movie Assistant. 🎬\nAsk me for recommendations, specific details, or search for titles!", 
      sender: "bot" 
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  
  // Auto-scroll ref
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setMessages((prev) => [...prev, { text: userMessage, sender: "user" }]);
    setInput("");
    setLoading(true);

    try {
      // Connects to your FastAPI backend
      const response = await fetch("http://127.0.0.1:8000/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { 
          text: data.response || "Error: No response.", 
          sender: "bot", 
          tool: data.tool_used 
        }
      ]);
    } catch (error) {
      console.error("API Error:", error);
      setMessages((prev) => [
        ...prev,
        { text: "Server Error: Is main.py running on port 8000?", sender: "bot" }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div className="app-container">
      <div className="chat-container">
        
        {/* HEADER */}
        <header>
          <div className="status-dot"></div>
          <h1>Endee CineBot Agent</h1>
        </header>

        {/* CHAT WINDOW */}
        <div className="chat-window">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender === "user" ? "user-msg" : "bot-msg"}`}>
              {/* Handle newlines in text */}
              {msg.text.split("\n").map((line, i) => (
                <span key={i}>
                  {line}
                  {i < msg.text.split("\n").length - 1 && <br />}
                </span>
              ))}
              
              {/* Tool Badge (Bot Only) */}
              {msg.tool && (
                <div className="tool-badge">Used Tool: {msg.tool}</div>
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* LOADING INDICATOR */}
        {loading && <div className="loading">Agent is typing...</div>}

        {/* INPUT AREA */}
        <div className="input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a movie query..."
            disabled={loading}
          />
          <button onClick={sendMessage} disabled={loading || !input.trim()}>
            Send
          </button>
        </div>

      </div>
    </div>
  );
}

export default App;