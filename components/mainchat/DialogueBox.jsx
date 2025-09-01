import { useState } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

export default function DialogueBox({ messages, setMessages, selectedNPCs = [] }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (input.trim() === "") return;

    const userMessage = { type: "player", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await axios.post("/api/chat", {
        input,
        selected_npcs: selectedNPCs
      });

      // 处理新的聊天格式
      if (response.data.chat_messages && Array.isArray(response.data.chat_messages)) {
        response.data.chat_messages.forEach(chatMsg => {
          setMessages((prev) => [...prev, chatMsg]);
        });
      } else {
        // 兼容旧格式
        const fallbackMessage = { 
          type: "narrative", 
          content: response.data.reply || "系统错误" 
        };
        setMessages((prev) => [...prev, fallbackMessage]);
      }
    } catch (error) {
      console.error("Error calling ChatGPT API:", error);
      const errorMessage = { type: "system", content: "Error: Unable to connect to server." };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderMessage = (msg, index) => {
    switch (msg.type) {
      case "player":
        return (
          <div key={index} className="flex justify-end">
            <div className="p-3 rounded-xl max-w-[70%] shadow-lg bg-emerald-900/60 text-emerald-300 backdrop-blur-sm">
              <strong className="block mb-1">玩家:</strong>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        );
      
      case "narrative":
        return (
          <div key={index} className="flex justify-start">
            <div className="p-3 rounded-xl max-w-[70%] shadow-lg bg-emerald-950/60 text-emerald-400 backdrop-blur-sm">
              <strong className="block mb-1">叙述:</strong>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        );
      
      case "npc":
        return (
          <div key={index} className="flex justify-start">
            <div className="p-3 rounded-xl max-w-[70%] shadow-lg bg-amber-900/60 text-amber-300 backdrop-blur-sm">
              <strong className="block mb-1">{msg.npc_name}:</strong>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        );
      
      case "system":
        return (
          <div key={index} className="flex justify-center">
            <div className="p-2 rounded-lg bg-red-900/60 text-red-300 text-sm">
              {msg.content}
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full rounded-lg">
      {/* 主聊天区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-lovecraft custom-scrollbar">
        {messages.map((msg, index) => renderMessage(msg, index))}
        {loading && (
          <div className="flex justify-start">
            <div className="text-emerald-500 text-sm">GM is typing...</div>
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="flex items-center p-4 border-t border-emerald-900/30 bg-black/40 backdrop-blur-sm rounded-b-lg">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          className="flex-1 bg-emerald-900/20 border border-emerald-900/30 rounded-lg px-4 py-2 text-emerald-400 focus:outline-none"
          placeholder="Enter your message..."
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className={`ml-4 px-4 py-2 rounded-lg font-semibold tracking-wide transition-all ${
            loading
              ? "bg-slate-800/50 text-slate-500 cursor-not-allowed"
              : "bg-emerald-900/50 text-emerald-400 hover:bg-emerald-800/50"
          }`}
        >
          Send
        </button>
      </div>
    </div>
  );
}