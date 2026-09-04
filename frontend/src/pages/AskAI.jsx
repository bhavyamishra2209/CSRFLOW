import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'
import { Send, Bot, User, FileText, AlertCircle } from 'lucide-react'

function AskAI() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I can answer questions about your uploaded documents. What would you like to know?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useKg, setUseKg] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!input.trim()) {
      return
    }

    const userMessage = input.trim()
    setInput('')
    
    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await api.query(userMessage, useKg)
      
      // Add assistant response
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.response,
          evidence: response.evidence || [],
          retrievedDocs: response.retrieved_documents || [],
          kgContext: response.kg_context,
        },
      ])
    } catch (err) {
      console.error('Query error:', err)
      
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${err.message}`,
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-12rem)] flex flex-col">
      <div className="mb-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Ask AI</h1>
        <div className="flex items-center justify-between">
          <p className="text-gray-600">
            Ask questions about your documents and get AI-powered answers with evidence citations
          </p>
          
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={useKg}
              onChange={(e) => setUseKg(e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-gray-700">Use Knowledge Graph</span>
          </label>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 card p-4 overflow-y-auto mb-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex items-start space-x-3 max-w-3xl ${
                  message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                }`}
              >
                {/* Avatar */}
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user'
                      ? 'bg-primary-600'
                      : message.error
                      ? 'bg-red-500'
                      : 'bg-gray-200'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User className="w-5 h-5 text-white" />
                  ) : (
                    <Bot className="w-5 h-5 text-gray-700" />
                  )}
                </div>

                {/* Message content */}
                <div
                  className={`rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : message.error
                      ? 'bg-red-50 border border-red-200'
                      : 'bg-gray-100'
                  }`}
                >
                  <p className={`text-sm whitespace-pre-wrap ${
                    message.role === 'user' ? 'text-white' : 'text-gray-900'
                  }`}>
                    {message.content}
                  </p>

                  {/* Evidence citations */}
                  {message.evidence && message.evidence.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-semibold text-gray-700 mb-2">
                        Evidence Citations:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {message.evidence.map((ev, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center space-x-1 px-2 py-1 bg-white rounded border border-gray-300 text-xs"
                            title={ev.evidence_snippet || 'Evidence reference'}
                          >
                            <FileText className="w-3 h-3 text-gray-500" />
                            <span className="text-gray-700 font-medium">
                              {ev.source_document || 'Document'}{ev.page && ev.page !== 'unknown' ? ` (p${ev.page})` : ''}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Retrieved documents */}
                  {message.retrievedDocs && message.retrievedDocs.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-semibold text-gray-700 mb-2">
                        Sources ({message.retrievedDocs.length}):
                      </p>
                      <div className="space-y-1">
                        {message.retrievedDocs.slice(0, 3).map((doc, idx) => (
                          <div key={idx} className="text-xs text-gray-600">
                            <span className="font-medium">
                              {doc.metadata?.filename || `Document ${idx + 1}`}
                            </span>
                            {doc.score && (
                              <span className="text-gray-500 ml-2">
                                ({(doc.score * 100).toFixed(0)}% relevant)
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Knowledge graph context */}
                  {message.kgContext && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs font-semibold text-gray-700 mb-1">
                        Knowledge Graph Enhanced
                      </p>
                      <p className="text-xs text-gray-600">
                        Used {message.kgContext.entities_used || 0} entities and{' '}
                        {message.kgContext.relations_used || 0} relationships
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                  <Bot className="w-5 h-5 text-gray-700" />
                </div>
                <div className="bg-gray-100 rounded-lg p-4">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="card p-4">
        <div className="flex space-x-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents..."
            className="flex-1 input"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn btn-primary flex items-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </div>
        
        <div className="mt-2 flex items-start space-x-2 text-xs text-gray-500">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <p>
            Responses are grounded in your documents with mandatory source citations. The AI will refuse to answer if information isn't found in your documents.
          </p>
        </div>
      </form>
    </div>
  )
}

export default AskAI
