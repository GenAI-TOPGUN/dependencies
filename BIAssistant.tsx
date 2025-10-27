import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Send, Bot, User, Sparkles, History, Sidebar, ChevronLeft, ChevronRight, ThumbsUp, ThumbsDown, Copy, Download, BarChart3, MoreVertical, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ChatHistory from "@/components/ChatHistory";
import { VegaLite } from "react-vega";
import datasourcesConfig from "@/config/datasources.json";

interface Message {
  id: string;
  type: 'user' | 'bot';
  content: string;
  timestamp: Date;
  chartSpec?: any;
  tableData?: any;
}

interface ChatSession {
  id: string;
  title: string;
  timestamp: Date;
  messageCount: number;
  messages: Message[];
}

const BIAssistant = () => {
  const { toast } = useToast();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const [isHistoryCollapsed, setIsHistoryCollapsed] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState("");
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [selectedDatasource, setSelectedDatasource] = useState(datasourcesConfig.datasources[0].id);
  const [isDatasourceDialogOpen, setIsDatasourceDialogOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const currentDatasource = datasourcesConfig.datasources.find(ds => ds.id === selectedDatasource) || datasourcesConfig.datasources[0];

  // localStorage functions
  const saveChatSessions = (sessions: ChatSession[]) => {
    localStorage.setItem('bi-assistant-sessions', JSON.stringify(sessions, (key, value) => {
      if (key === 'timestamp' && value instanceof Date) return value.toISOString();
      return value;
    }));
  };

  const loadChatSessions = (): ChatSession[] => {
    try {
      const saved = localStorage.getItem('bi-assistant-sessions');
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.map((session: any) => ({
          ...session,
          timestamp: new Date(session.timestamp),
          messages: session.messages?.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          })) || []
        }));
      }
    } catch (error) {
      console.error('Error loading chat sessions:', error);
    }
    return [];
  };

  const saveCurrentSession = () => {
    if (currentSessionId && messages.length > 0) {
      setChatSessions(prev => {
        const updated = prev.map(session => 
          session.id === currentSessionId 
            ? { ...session, messages, messageCount: messages.length }
            : session
        );
        saveChatSessions(updated);
        return updated;
      });
    }
  };

  // Initialize from localStorage
  useEffect(() => {
    const savedSessions = loadChatSessions();
    if (savedSessions.length > 0) {
      setChatSessions(savedSessions);
      setCurrentSessionId(savedSessions[0].id);
      setMessages(savedSessions[0].messages);
    } else {
      const initialSession: ChatSession = {
        id: "1",
        title: "BI Assistant Chat",
        timestamp: new Date(),
        messageCount: 1,
        messages: [{
          id: '1',
          type: 'bot',
          content: "Hello! I'm your Business Intelligence assistant. I can help you visualize data, analyze trends, and generate insights. Ask me anything about your data!",
          timestamp: new Date()
        }]
      };
      setChatSessions([initialSession]);
      setCurrentSessionId(initialSession.id);
      setMessages(initialSession.messages);
      saveChatSessions([initialSession]);
    }
  }, []);

  useEffect(() => {
    if (currentSessionId && messages.length > 0) {
      saveCurrentSession();
    }
  }, [messages, currentSessionId]);

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleNewChat = () => {
    const initialMessage = {
      id: '1',
      type: 'bot' as const,
      content: "Hello! I'm your Business Intelligence assistant. What insights can I help you discover today?",
      timestamp: new Date()
    };
    
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: "New BI Chat",
      timestamp: new Date(),
      messageCount: 1,
      messages: [initialMessage]
    };
    
    setChatSessions(prev => {
      const updated = [newSession, ...prev];
      saveChatSessions(updated);
      return updated;
    });
    setCurrentSessionId(newSession.id);
    setMessages([initialMessage]);
  };

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    const selectedSession = chatSessions.find(s => s.id === sessionId);
    if (selectedSession) {
      setMessages(selectedSession.messages);
    }
  };

  const handleDeleteSession = (sessionId: string) => {
    setChatSessions(prev => {
      const updated = prev.filter(s => s.id !== sessionId);
      saveChatSessions(updated);
      
      if (currentSessionId === sessionId && updated.length > 0) {
        setCurrentSessionId(updated[0].id);
        setMessages(updated[0].messages);
      } else if (updated.length === 0) {
        const newSession: ChatSession = {
          id: Date.now().toString(),
          title: "BI Assistant Chat",
          timestamp: new Date(),
          messageCount: 1,
          messages: [{
            id: '1',
            type: 'bot',
            content: "Hello! I'm your Business Intelligence assistant. What can I help you analyze?",
            timestamp: new Date()
          }]
        };
        setCurrentSessionId(newSession.id);
        setMessages(newSession.messages);
        saveChatSessions([newSession]);
        return [newSession];
      }
      
      return updated;
    });
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsTyping(true);

    // Simulate API response with different response types
    setTimeout(() => {
      const responseType = Math.floor(Math.random() * 3);
      let botResponse: Message;

      if (responseType === 0) {
        // Chart response
        botResponse = {
          id: (Date.now() + 1).toString(),
          type: 'bot',
          content: "Here's a visualization of the sales trends over the last quarter:",
          timestamp: new Date(),
          chartSpec: {
            $schema: "https://vega.github.io/schema/vega-lite/v5.json",
            description: "Sales trends visualization",
            data: {
              values: [
                { month: "Jan", sales: 28000, profit: 12000 },
                { month: "Feb", sales: 35000, profit: 15000 },
                { month: "Mar", sales: 42000, profit: 18000 },
                { month: "Apr", sales: 38000, profit: 16500 },
                { month: "May", sales: 45000, profit: 20000 },
                { month: "Jun", sales: 52000, profit: 23000 }
              ]
            },
            mark: { type: "line", point: true, tooltip: true },
            encoding: {
              x: { field: "month", type: "ordinal", title: "Month" },
              y: { field: "sales", type: "quantitative", title: "Sales ($)" },
              color: { value: "hsl(var(--primary))" }
            },
            width: 600,
            height: 300
          }
        };
      } else if (responseType === 1) {
        // Table response
        botResponse = {
          id: (Date.now() + 1).toString(),
          type: 'bot',
          content: "Here's a breakdown of the top performing products:",
          timestamp: new Date(),
          tableData: {
            headers: ["Product", "Revenue", "Units Sold", "Growth"],
            rows: [
              ["Product A", "$125,000", "2,450", "+15%"],
              ["Product B", "$98,000", "1,820", "+8%"],
              ["Product C", "$87,500", "1,650", "+22%"],
              ["Product D", "$76,200", "1,420", "+5%"],
              ["Product E", "$65,800", "1,230", "+18%"]
            ]
          }
        };
      } else {
        // Text-only response
        botResponse = {
          id: (Date.now() + 1).toString(),
          type: 'bot',
          content: `Based on the analysis of your data:

**Key Insights:**
• Revenue has grown by 18% compared to the previous quarter
• Customer acquisition costs decreased by 12%
• Product A shows the highest ROI at 35%
• Regional performance varies significantly, with the West region leading at 42% growth

**Recommendations:**
1. Increase marketing budget for Product A due to high ROI
2. Focus on customer retention strategies in underperforming regions
3. Optimize pricing strategy for Product C to improve margins
4. Consider expanding distribution channels in the West region

Would you like me to create a detailed visualization or drill down into any specific metric?`,
          timestamp: new Date()
        };
      }
      
      setMessages(prev => [...prev, botResponse]);
      setIsTyping(false);
    }, 2000);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFeedback = (messageId: string, type: 'positive' | 'negative') => {
    toast({
      title: "Feedback recorded",
      description: `Thank you for your ${type} feedback!`,
    });
  };

  const handleCopyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
    toast({
      title: "Copied",
      description: "Message copied to clipboard",
    });
  };

  const handleDownload = (content: string, format: string) => {
    const blob = new Blob([content], { type: `text/${format}` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bi-response.${format}`;
    a.click();
    URL.revokeObjectURL(url);
    toast({
      title: "Downloaded",
      description: `Response downloaded as ${format}`,
    });
  };

  const renderMessageContent = (message: Message) => {
    return (
      <div className="space-y-4">
        {/* Text content */}
        <div className="prose prose-sm max-w-none dark:prose-invert">
          {message.content}
        </div>

        {/* Chart visualization */}
        {message.chartSpec && (
          <Card className="overflow-hidden bg-card/50 backdrop-blur-sm">
            <CardContent className="p-6">
              <VegaLite 
                spec={message.chartSpec} 
                actions={false}
              />
            </CardContent>
          </Card>
        )}

        {/* Table data */}
        {message.tableData && (
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      {message.tableData.headers.map((header: string, idx: number) => (
                        <th key={idx} className="px-4 py-3 text-left text-sm font-semibold">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {message.tableData.rows.map((row: string[], rowIdx: number) => (
                      <tr key={rowIdx} className="border-t border-border/50 hover:bg-muted/30">
                        {row.map((cell: string, cellIdx: number) => (
                          <td key={cellIdx} className="px-4 py-3 text-sm">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  const handleRenameSession = (sessionId: string, newTitle: string) => {
    setChatSessions(prev => {
      const updated = prev.map(session => 
        session.id === sessionId 
          ? { ...session, title: newTitle }
          : session
      );
      saveChatSessions(updated);
      return updated;
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex flex-col">
      <Header />
      
      <div className="flex-1 flex relative h-[calc(100vh-4rem)]">
        {/* Sidebar History - Sticky */}
        <div className={cn(
          "transition-all duration-300 ease-in-out bg-background/95 backdrop-blur-sm border-r border-border/50 flex flex-col h-[calc(100vh-4rem)] z-30 overflow-hidden",
          showHistory ? (isHistoryCollapsed ? "w-16" : "w-80") : "w-0 opacity-0"
        )}>
          {showHistory && (
            <>
              <div className="p-4 border-b border-border/50 flex-shrink-0">
                <div className="flex items-center justify-between">
                  {!isHistoryCollapsed && (
                    <h2 className="font-semibold text-sm">Chat History</h2>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsHistoryCollapsed(!isHistoryCollapsed)}
                    className="h-8 w-8 p-0"
                  >
                    {isHistoryCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              {!isHistoryCollapsed && (
                <div className="flex-1 overflow-hidden">
                  <ChatHistory
                    sessions={chatSessions}
                    currentSessionId={currentSessionId}
                    onSelectSession={handleSelectSession}
                    onNewChat={handleNewChat}
                    onDeleteSession={handleDeleteSession}
                    onRenameSession={handleRenameSession}
                  />
                </div>
              )}

              {isHistoryCollapsed && (
                <div className="flex-shrink-0 flex flex-col items-center pt-4 space-y-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleNewChat}
                    className="h-10 w-10 p-0"
                    title="New Chat"
                  >
                    <Sparkles className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-10 w-10 p-0"
                    title="Chat History"
                  >
                    <History className="h-4 w-4" />
                  </Button>
                  <Dialog open={isDatasourceDialogOpen} onOpenChange={setIsDatasourceDialogOpen}>
                    <DialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-10 w-10 p-0"
                        title="Data Sources"
                      >
                        <Database className="h-4 w-4" />
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle>Data Source Configuration</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-6 py-4">
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Select Data Source</label>
                          <Select value={selectedDatasource} onValueChange={setSelectedDatasource}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {datasourcesConfig.datasources.map((ds) => (
                                <SelectItem key={ds.id} value={ds.id}>
                                  {ds.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <Card>
                          <CardHeader>
                            <CardTitle className="text-base">Data Source Details</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <div>
                              <p className="text-sm font-medium text-muted-foreground mb-1">Definition</p>
                              <p className="text-sm">{currentDatasource.definition}</p>
                            </div>
                            
                            <div>
                              <p className="text-sm font-medium text-muted-foreground mb-1">LUID</p>
                              <code className="text-xs bg-muted px-2 py-1 rounded">{currentDatasource.luid}</code>
                            </div>

                            <div>
                              <p className="text-sm font-medium mb-2">Attributes</p>
                              <div className="space-y-3">
                                {currentDatasource.attributes.map((attr, idx) => (
                                  <div key={idx} className="border-l-2 border-primary/30 pl-3 py-1">
                                    <div className="flex items-center gap-2">
                                      <code className="text-xs font-semibold">{attr.name}</code>
                                      <Badge variant="outline" className="text-xs">{attr.type}</Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">{attr.description}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              )}

              {!isHistoryCollapsed && (
                <div className="p-4 border-t border-border/50 flex-shrink-0">
                  <Dialog open={isDatasourceDialogOpen} onOpenChange={setIsDatasourceDialogOpen}>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm" className="w-full gap-2">
                        <Database className="h-4 w-4" />
                        Data Sources
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle>Data Source Configuration</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-6 py-4">
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Select Data Source</label>
                          <Select value={selectedDatasource} onValueChange={setSelectedDatasource}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {datasourcesConfig.datasources.map((ds) => (
                                <SelectItem key={ds.id} value={ds.id}>
                                  {ds.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <Card>
                          <CardHeader>
                            <CardTitle className="text-base">Data Source Details</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <div>
                              <p className="text-sm font-medium text-muted-foreground mb-1">Definition</p>
                              <p className="text-sm">{currentDatasource.definition}</p>
                            </div>
                            
                            <div>
                              <p className="text-sm font-medium text-muted-foreground mb-1">LUID</p>
                              <code className="text-xs bg-muted px-2 py-1 rounded">{currentDatasource.luid}</code>
                            </div>

                            <div>
                              <p className="text-sm font-medium mb-2">Attributes</p>
                              <div className="space-y-3">
                                {currentDatasource.attributes.map((attr, idx) => (
                                  <div key={idx} className="border-l-2 border-primary/30 pl-3 py-1">
                                    <div className="flex items-center gap-2">
                                      <code className="text-xs font-semibold">{attr.name}</code>
                                      <Badge variant="outline" className="text-xs">{attr.type}</Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">{attr.description}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              )}
            </>
          )}
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col relative">
          {/* Header Controls - Sticky */}
          <div className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur-sm px-6 py-4 shadow-sm flex-shrink-0">
            <div className="flex items-start gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
                className="hover:bg-primary/10 mt-1"
              >
                <Sidebar className="h-4 w-4" />
              </Button>
              <div className="flex-1">
                <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
                  BI Assistant
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                  AI-powered business intelligence and data visualization • Connected to: <span className="font-medium text-foreground">{currentDatasource.name}</span>
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="gap-1">
                  <BarChart3 className="h-3 w-3" />
                  Analytics Ready
                </Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleNewChat}
                  className="gap-2"
                >
                  <Sparkles className="h-4 w-4" />
                  New Chat
                </Button>
              </div>
            </div>
          </div>

          {/* Messages Area - Scrollable */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500",
                    message.type === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {message.type === 'bot' && (
                    <Avatar className="h-10 w-10 border-2 border-primary/20 shadow-lg">
                      <AvatarFallback className="bg-gradient-to-br from-primary to-primary/70">
                        <Bot className="h-5 w-5 text-primary-foreground" />
                      </AvatarFallback>
                    </Avatar>
                  )}

                  <div
                    className={cn(
                      "rounded-2xl px-6 py-4 max-w-[80%] shadow-md",
                      message.type === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-card border border-border/50'
                    )}
                  >
                    {message.type === 'user' ? (
                      <p className="whitespace-pre-wrap break-words">{message.content}</p>
                    ) : (
                      <>
                        {renderMessageContent(message)}
                        
                        {/* Bot message actions */}
                        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border/50">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2"
                            onClick={() => handleFeedback(message.id, 'positive')}
                          >
                            <ThumbsUp className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2"
                            onClick={() => handleFeedback(message.id, 'negative')}
                          >
                            <ThumbsDown className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2"
                            onClick={() => handleCopyMessage(message.content)}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm" className="h-8 px-2">
                                <MoreVertical className="h-3 w-3" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handleDownload(message.content, 'txt')}>
                                <Download className="h-4 w-4 mr-2" />
                                Download as Text
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleDownload(message.content, 'md')}>
                                <Download className="h-4 w-4 mr-2" />
                                Download as Markdown
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </>
                    )}
                  </div>

                  {message.type === 'user' && (
                    <Avatar className="h-10 w-10 border-2 border-primary shadow-lg">
                      <AvatarFallback className="bg-gradient-to-br from-primary/80 to-primary">
                        <User className="h-5 w-5 text-primary-foreground" />
                      </AvatarFallback>
                    </Avatar>
                  )}
                </div>
              ))}

              {isTyping && (
                <div className="flex gap-4 animate-in fade-in slide-in-from-bottom-4">
                  <Avatar className="h-10 w-10 border-2 border-primary/20">
                    <AvatarFallback className="bg-gradient-to-br from-primary to-primary/70">
                      <Bot className="h-5 w-5 text-primary-foreground" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="rounded-2xl px-6 py-4 bg-card border border-border/50">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area - Sticky */}
          <div className="border-t bg-background/95 backdrop-blur-sm px-6 py-4 flex-shrink-0">
            <div className="max-w-4xl mx-auto">
              <div className="relative">
                <Textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask about trends, request visualizations, or analyze your data..."
                  className="min-h-[60px] pr-12 resize-none rounded-xl border-2 focus:border-primary/50 transition-colors"
                  disabled={isTyping}
                />
                <Button
                  onClick={handleSendMessage}
                  size="sm"
                  disabled={!inputMessage.trim() || isTyping}
                  className="absolute bottom-3 right-3 h-9 w-9 rounded-lg shadow-lg hover:shadow-xl transition-shadow"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-2 text-center">
                Press Enter to send, Shift+Enter for new line
              </p>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
};

export default BIAssistant;
