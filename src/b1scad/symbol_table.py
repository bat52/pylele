#!/usr/bin/env python3
"""
Symbol table and scope management for OpenSCAD language.

Manages variables, functions, and modules within their proper scopes,
enabling name resolution, variable lookup, and scope hierarchy tracking.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Symbol:
    """Represents a symbol (variable, function, or module)."""
    name: str
    symbol_type: str  # 'variable', 'function', 'module'
    value: Any = None
    parameters: List[str] = None
    line: int = 0
    
    def __init__(self, name: str, symbol_type: str, value: Any = None, 
                 parameters: List[str] = None, line: int = 0):
        self.name = name
        self.symbol_type = symbol_type
        self.value = value
        self.parameters = parameters or []
        self.line = line


class Scope:
    """Represents a scope level in the symbol table."""
    
    def __init__(self, parent: Optional[Scope] = None, scope_type: str = 'block'):
        self.parent = parent
        self.scope_type = scope_type  # 'module', 'function', 'for', 'let', 'block'
        self.symbols: Dict[str, Symbol] = {}
        self.children: List[Scope] = []
    
    def define(self, name: str, symbol_type: str, value: Any = None, 
               parameters: List[str] = None, line: int = 0) -> Symbol:
        """Define a new symbol in this scope."""
        symbol = Symbol(name, symbol_type, value, parameters, line)
        self.symbols[name] = symbol
        return symbol
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol, checking this scope and parent scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
    
    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up a symbol only in this scope (not parents)."""
        return self.symbols.get(name)
    
    def redefine(self, name: str, value: Any) -> Optional[Symbol]:
        """Redefine an existing symbol's value."""
        symbol = self.lookup(name)
        if symbol:
            symbol.value = value
        return symbol
    
    def get_all_symbols(self) -> Dict[str, Symbol]:
        """Get all symbols in this scope and parents."""
        symbols = {}
        if self.parent:
            symbols.update(self.parent.get_all_symbols())
        symbols.update(self.symbols)
        return symbols


class SymbolTable:
    """Main symbol table for managing scopes."""
    
    def __init__(self):
        self.root_scope = Scope(scope_type='module')
        self.current_scope = self.root_scope
        self.scopes_stack: List[Scope] = [self.root_scope]
        self.errors: List[str] = []
    
    def push_scope(self, scope_type: str = 'block') -> Scope:
        """Create and enter a new scope."""
        new_scope = Scope(parent=self.current_scope, scope_type=scope_type)
        self.current_scope.children.append(new_scope)
        self.scopes_stack.append(new_scope)
        self.current_scope = new_scope
        return new_scope
    
    def pop_scope(self) -> Scope:
        """Exit the current scope and return to parent."""
        if len(self.scopes_stack) > 1:
            old_scope = self.scopes_stack.pop()
            self.current_scope = self.scopes_stack[-1]
            return old_scope
        return self.current_scope
    
    def define(self, name: str, symbol_type: str, value: Any = None, 
               parameters: List[str] = None, line: int = 0) -> Symbol:
        """Define a symbol in the current scope."""
        # Check for redefinition in the same scope
        if name in self.current_scope.symbols:
            self.add_error(f"Redefinition of '{name}' at line {line}")
        return self.current_scope.define(name, symbol_type, value, parameters, line)
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol."""
        return self.current_scope.lookup(name)
    
    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up a symbol in the current scope only."""
        return self.current_scope.lookup_local(name)
    
    def set_value(self, name: str, value: Any, line: int = 0) -> Optional[Symbol]:
        """Set the value of an existing symbol."""
        symbol = self.current_scope.lookup(name)
        if not symbol:
            self.add_error(f"Undefined symbol '{name}' at line {line}")
            return None
        symbol.value = value
        return symbol
    
    def add_error(self, error_message: str):
        """Record a semantic error."""
        self.errors.append(error_message)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def report_errors(self) -> str:
        """Get a formatted error report."""
        if not self.errors:
            return ""
        return "Symbol table errors:\n" + "\n".join(self.errors)
    
    def get_current_scope_symbols(self) -> Dict[str, Symbol]:
        """Get all symbols visible in the current scope."""
        return self.current_scope.get_all_symbols()
    
    def reset(self):
        """Reset the symbol table."""
        self.root_scope = Scope(scope_type='module')
        self.current_scope = self.root_scope
        self.scopes_stack = [self.root_scope]
        self.errors = []
