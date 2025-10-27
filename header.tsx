import { useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

  const menuItems = [
    {
      name: "RAG System",
      items: [
        { name: "RAG Upload", link: "/rag-upload", description: "Upload PDF documents for indexing" },
        { name: "RAG Configuration", link: "/rag-configuration", description: "Configure indexing and search settings" },
        { name: "RAG Search", link: "/rag-search", description: "Search through indexed documents" }
      ]
    },
    {
      name: "Knowledge Discovery",
      link: "/knowledge-discovery"
    },
    {
      name: "BI Assistant",
      link: "/bi-assistant"
    },
    {
      name: "Company",
      items: [
        { name: "About", link: "#" },
        { name: "Contact", link: "#" }
      ]
    }
  ];

  const toggleDropdown = (name: string) => {
    setActiveDropdown(activeDropdown === name ? null : name);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border" style={{backgroundColor: '#0066cc', color: 'white'}}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <h1 className="text-2xl font-bold text-white">
                RAG Knowledge
              </h1>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-8">
            {menuItems.map((menu) => (
              <div key={menu.name} className="relative">
                {menu.items ? (
                  <>
                    <button
                      onClick={() => toggleDropdown(menu.name)}
                      className="nav-link flex items-center space-x-1 py-2 text-sm font-medium text-white hover:text-gray-200"
                    >
                      <span>{menu.name}</span>
                      <ChevronDown 
                        className={`h-4 w-4 transition-transform ${
                          activeDropdown === menu.name ? 'rotate-180' : ''
                        }`} 
                      />
                    </button>
                    
                    {/* Dropdown Menu */}
                    {activeDropdown === menu.name && (
                      <div className="absolute top-full left-0 mt-1 w-80 dropdown-menu py-2">
                        {menu.items.map((item) => (
                          <Link
                            key={item.name}
                            to={item.link}
                            className="block px-4 py-3 text-sm text-foreground hover:bg-muted transition-smooth"
                          >
                            <div className="font-medium">{item.name}</div>
                            {item.description && (
                              <div className="text-xs text-muted-foreground mt-1">{item.description}</div>
                            )}
                          </Link>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <Link
                    to={menu.link || "#"}
                    className="nav-link flex items-center py-2 text-sm font-medium text-white hover:text-gray-200"
                  >
                    {menu.name}
                  </Link>
                )}
              </div>
            ))}
          </nav>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            <Button variant="ghost" className="text-sm font-medium">
              Sign In
            </Button>
            <Button className="text-sm font-medium shadow-elegant">
              Get Started
            </Button>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-white hover:text-gray-200 transition-smooth"
            >
              {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 border-t border-border bg-card">
              {menuItems.map((menu) => (
                <div key={menu.name} className="space-y-1">
                  {menu.items ? (
                    <>
                      <button
                        onClick={() => toggleDropdown(menu.name)}
                        className="w-full text-left px-3 py-2 text-base font-medium text-foreground hover:text-primary transition-smooth flex items-center justify-between"
                      >
                        {menu.name}
                        <ChevronDown 
                          className={`h-4 w-4 transition-transform ${
                            activeDropdown === menu.name ? 'rotate-180' : ''
                          }`} 
                        />
                      </button>
                      {activeDropdown === menu.name && (
                        <div className="pl-4 space-y-1">
                          {menu.items.map((item) => (
                            <Link
                              key={item.name}
                              to={item.link}
                              className="block px-3 py-2 text-sm text-muted-foreground hover:text-primary transition-smooth"
                            >
                              {item.name}
                            </Link>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <Link
                      to={menu.link || "#"}
                      className="block px-3 py-2 text-base font-medium text-foreground hover:text-primary transition-smooth"
                    >
                      {menu.name}
                    </Link>
                  )}
                </div>
              ))}
              <div className="pt-4 pb-3 border-t border-border">
                <div className="space-y-3">
                  <Button variant="ghost" className="w-full justify-start">
                    Sign In
                  </Button>
                  <Button className="w-full shadow-elegant">
                    Get Started
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
