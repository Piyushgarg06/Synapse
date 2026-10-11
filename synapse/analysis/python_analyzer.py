"""Python-specific structural analysis using tree-sitter."""

from __future__ import annotations

from tree_sitter import Node

from synapse.models import (
    SymbolInfo, SymbolKind, SourceLocation, ReferenceInfo, ReferenceStatus,
    ImportInfo, InheritanceInfo, CallInfo, FileAnalysis,
)


def _make_location(node: Node) -> SourceLocation:
    """Create a SourceLocation from a tree-sitter node."""
    return SourceLocation(
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        start_line=node.start_point[0] + 1,  # Convert to 1-based
        start_column=node.start_point[1],
        end_line=node.end_point[0] + 1,
        end_column=node.end_point[1],
    )


def _get_node_text(node: Node, source: bytes) -> str:
    """Extract text from a node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def analyze_python(root_node: Node, source: bytes, file_path: str) -> FileAnalysis:
    """Analyze a Python source file.
    
    Extracts: modules, classes, methods, functions, imports, calls, inheritance.
    """
    analysis = FileAnalysis(file_path=file_path, language="python")
    
    # Track name occurrences for ordinal disambiguation
    name_counts: dict[tuple[str, str], int] = {}  # (qualified_name, kind) -> count
    
    def _get_ordinal(qualified_name: str, kind: str) -> int:
        key = (qualified_name, kind)
        count = name_counts.get(key, 0)
        name_counts[key] = count + 1
        return count
    
    def _extract_symbols(node: Node, parent_qualified_name: str = ""):
        """Recursively extract symbols from the AST."""
        for child in node.children:
            if child.type == "function_definition":
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = _get_node_text(name_node, source)
                    qualified = f"{parent_qualified_name}.{name}" if parent_qualified_name else name
                    
                    # Determine if this is a method (inside a class)
                    kind = SymbolKind.METHOD if parent_qualified_name and _is_inside_class(node) else SymbolKind.FUNCTION
                    ordinal = _get_ordinal(qualified, kind.value)
                    
                    symbol = SymbolInfo(
                        name=name,
                        qualified_name=qualified,
                        kind=kind,
                        file_path=file_path,
                        location=_make_location(child),
                        ordinal=ordinal,
                    )
                    analysis.symbols.append(symbol)
                    
                    # Extract calls within the function body
                    body = child.child_by_field_name("body")
                    if body:
                        _extract_calls(body, qualified)
                        _extract_symbols(body, qualified)
                    
            elif child.type == "class_definition":
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = _get_node_text(name_node, source)
                    qualified = f"{parent_qualified_name}.{name}" if parent_qualified_name else name
                    ordinal = _get_ordinal(qualified, SymbolKind.CLASS.value)
                    
                    symbol = SymbolInfo(
                        name=name,
                        qualified_name=qualified,
                        kind=SymbolKind.CLASS,
                        file_path=file_path,
                        location=_make_location(child),
                        ordinal=ordinal,
                    )
                    analysis.symbols.append(symbol)
                    
                    # Extract inheritance
                    _extract_inheritance(child, name)
                    
                    # Recurse into class body
                    body = child.child_by_field_name("body")
                    if body:
                        _extract_symbols(body, qualified)
            
            elif child.type == "decorated_definition":
                # Handle decorated functions/classes
                _extract_symbols(child, parent_qualified_name)
            
            elif child.type == "import_statement":
                _extract_import(child)
            
            elif child.type == "import_from_statement":
                _extract_from_import(child)
    
    def _is_inside_class(node: Node) -> bool:
        """Check if the parent context is a class body."""
        parent = node.parent
        while parent:
            if parent.type == "class_definition":
                return True
            if parent.type == "function_definition":
                return False
            parent = parent.parent
        return False
    
    def _extract_inheritance(class_node: Node, class_name: str):
        """Extract base classes from a class definition."""
        superclasses = class_node.child_by_field_name("superclasses")
        if superclasses:
            for arg in superclasses.children:
                if arg.type == "identifier":
                    base_name = _get_node_text(arg, source)
                    analysis.inheritance.append(InheritanceInfo(
                        class_name=class_name,
                        base_class_name=base_name,
                        file_path=file_path,
                    ))
                elif arg.type == "attribute":
                    base_name = _get_node_text(arg, source)
                    analysis.inheritance.append(InheritanceInfo(
                        class_name=class_name,
                        base_class_name=base_name,
                        file_path=file_path,
                    ))
    
    def _extract_import(import_node: Node):
        """Extract 'import X' statements."""
        for child in import_node.children:
            if child.type == "dotted_name":
                module_name = _get_node_text(child, source)
                analysis.imports.append(ImportInfo(
                    module_name=module_name,
                    file_path=file_path,
                    location=_make_location(import_node),
                ))
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                alias_node = child.child_by_field_name("alias")
                if name_node:
                    module_name = _get_node_text(name_node, source)
                    alias = _get_node_text(alias_node, source) if alias_node else None
                    analysis.imports.append(ImportInfo(
                        module_name=module_name,
                        alias=alias,
                        file_path=file_path,
                        location=_make_location(import_node),
                    ))
    
    def _extract_from_import(import_node: Node):
        """Extract 'from X import Y' statements."""
        module_node = child_by_field_name_safe(import_node, "module_name")
        module_name = _get_node_text(module_node, source) if module_node else ""
        
        imported_names = []
        for child in import_node.children:
            if child.type == "import_prefix":
                # Relative import dots
                if not module_name:
                    module_name = _get_node_text(child, source)
                else:
                    module_name = _get_node_text(child, source) + module_name
            elif child.type == "dotted_name" and child != module_node:
                imported_names.append(_get_node_text(child, source))
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                if name_node:
                    imported_names.append(_get_node_text(name_node, source))
            elif child.type == "wildcard_import":
                imported_names.append("*")
        
        analysis.imports.append(ImportInfo(
            module_name=module_name,
            imported_names=imported_names,
            file_path=file_path,
            location=_make_location(import_node),
        ))
    
    def _extract_calls(node: Node, caller_qualified_name: str):
        """Extract function calls from a node."""
        for child in node.children:
            if child.type == "call":
                func_node = child.child_by_field_name("function")
                if func_node:
                    callee_name = _get_node_text(func_node, source)
                    analysis.calls.append(CallInfo(
                        caller_qualified_name=caller_qualified_name,
                        callee_name=callee_name,
                        file_path=file_path,
                        location=_make_location(child),
                    ))
                    # Also add as a reference
                    analysis.references.append(ReferenceInfo(
                        name=callee_name,
                        file_path=file_path,
                        location=_make_location(func_node),
                        status=ReferenceStatus.SYNTACTIC,
                        context_qualified_name=caller_qualified_name,
                    ))
                # Recurse into call arguments
                _extract_calls(child, caller_qualified_name)
            elif child.type in ("if_statement", "for_statement", "while_statement",
                               "with_statement", "try_statement", "block",
                               "expression_statement", "return_statement",
                               "assignment", "augmented_assignment",
                               "assert_statement", "raise_statement"):
                _extract_calls(child, caller_qualified_name)
            elif child.type in ("list", "tuple", "dictionary", "set",
                               "list_comprehension", "dictionary_comprehension",
                               "set_comprehension", "generator_expression",
                               "conditional_expression", "binary_operator",
                               "unary_operator", "boolean_operator",
                               "comparison_operator", "not_operator",
                               "parenthesized_expression", "subscript",
                               "attribute", "pair", "keyword_argument",
                               "yield", "await"):
                _extract_calls(child, caller_qualified_name)
    
    # Extract module-level symbols
    _extract_symbols(root_node)
    
    return analysis


def child_by_field_name_safe(node: Node, name: str):
    """Safely get a child by field name, returning None if not found."""
    try:
        return node.child_by_field_name(name)
    except Exception:
        return None
