"""TypeScript-specific structural analysis using tree-sitter.

TypeScript shares much of its syntax with JavaScript but adds type annotations,
interfaces, enums, and other constructs. We handle TS and TSX using the
TypeScript grammar from tree-sitter-typescript.
"""

from __future__ import annotations

from tree_sitter import Node

from synapse.models import (
    SymbolInfo, SymbolKind, SourceLocation, ReferenceInfo, ReferenceStatus,
    ImportInfo, InheritanceInfo, CallInfo, FileAnalysis,
)


def _make_location(node: Node) -> SourceLocation:
    return SourceLocation(
        start_byte=node.start_byte,
        end_byte=node.end_byte,
        start_line=node.start_point[0] + 1,
        start_column=node.start_point[1],
        end_line=node.end_point[0] + 1,
        end_column=node.end_point[1],
    )


def _get_node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_type_name(node: Node, source: bytes) -> Optional[str]:
    """Extract a type/class/interface name from an AST node."""
    if node.type in ("identifier", "type_identifier", "nested_identifier", "nested_type_identifier", "member_expression"):
        return _get_node_text(node, source)
    if node.type == "generic_type":
        for child in node.children:
            name = _extract_type_name(child, source)
            if name:
                return name
    return None


def analyze_typescript(root_node: Node, source: bytes, file_path: str, language: str = "typescript") -> FileAnalysis:
    """Analyze a TypeScript or TSX source file.
    
    Extracts: functions, classes, methods, imports, exports, calls, inheritance, interfaces, enums.
    """
    analysis = FileAnalysis(file_path=file_path, language=language)
    name_counts: dict[tuple[str, str], int] = {}
    
    def _get_ordinal(qualified_name: str, kind: str) -> int:
        key = (qualified_name, kind)
        count = name_counts.get(key, 0)
        name_counts[key] = count + 1
        return count
    
    def _extract_symbols(node: Node, parent_qn: str = ""):
        for child in node.children:
            if child.type == "function_declaration":
                _extract_function(child, parent_qn)
            elif child.type in ("class_declaration", "abstract_class_declaration"):
                _extract_class(child, parent_qn)
            elif child.type in ("lexical_declaration", "variable_declaration"):
                _extract_variable_decl(child, parent_qn)
            elif child.type == "export_statement":
                _extract_export(child, parent_qn)
            elif child.type == "import_statement":
                _extract_import(child)
            elif child.type == "interface_declaration":
                _extract_interface(child, parent_qn)
            elif child.type == "type_alias_declaration":
                pass
            elif child.type == "enum_declaration":
                _extract_enum(child, parent_qn)
            elif child.type in ("statement_block", "expression_statement"):
                _extract_symbols(child, parent_qn)
    
    def _extract_function(node: Node, parent_qn: str):
        name_node = node.child_by_field_name("name")
        if name_node:
            name = _get_node_text(name_node, source)
            qn = f"{parent_qn}.{name}" if parent_qn else name
            kind = SymbolKind.FUNCTION
            ordinal = _get_ordinal(qn, kind.value)
            
            analysis.symbols.append(SymbolInfo(
                name=name, qualified_name=qn, kind=kind,
                file_path=file_path, location=_make_location(node),
                ordinal=ordinal,
            ))
            
            body = node.child_by_field_name("body")
            if body:
                _extract_calls(body, qn)
                _extract_symbols(body, qn)
    
    def _extract_class(node: Node, parent_qn: str):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = _get_node_text(name_node, source)
        qn = f"{parent_qn}.{name}" if parent_qn else name
        ordinal = _get_ordinal(qn, SymbolKind.CLASS.value)
        
        analysis.symbols.append(SymbolInfo(
            name=name, qualified_name=qn, kind=SymbolKind.CLASS,
            file_path=file_path, location=_make_location(node),
            ordinal=ordinal,
        ))
        
        # Extract inheritance (extends and implements)
        for c in node.children:
            if c.type == "class_heritage":
                for heritage_child in c.children:
                    if heritage_child.type == "extends_clause":
                        for id_node in heritage_child.children:
                            base_name = _extract_type_name(id_node, source)
                            if base_name:
                                analysis.inheritance.append(InheritanceInfo(
                                    class_name=name,
                                    base_class_name=base_name,
                                    file_path=file_path,
                                ))
                    elif heritage_child.type == "implements_clause":
                        for id_node in heritage_child.children:
                            iface_name = _extract_type_name(id_node, source)
                            if iface_name:
                                analysis.inheritance.append(InheritanceInfo(
                                    class_name=name,
                                    base_class_name=iface_name,
                                    file_path=file_path,
                                ))
        
        # Extract methods from class body
        body = node.child_by_field_name("body")
        if body:
            for member in body.children:
                if member.type in ("method_definition", "abstract_method_signature"):
                    _extract_method(member, qn)
                elif member.type == "public_field_definition":
                    prop = member.child_by_field_name("name")
                    val = member.child_by_field_name("value")
                    if prop and val and val.type in ("arrow_function", "function_expression"):
                        method_name = _get_node_text(prop, source)
                        method_qn = f"{qn}.{method_name}"
                        ordinal = _get_ordinal(method_qn, SymbolKind.METHOD.value)
                        analysis.symbols.append(SymbolInfo(
                            name=method_name, qualified_name=method_qn,
                            kind=SymbolKind.METHOD, file_path=file_path,
                            location=_make_location(member), ordinal=ordinal,
                        ))
                        body_node = val.child_by_field_name("body")
                        if body_node:
                            _extract_calls(body_node, method_qn)
                            _extract_symbols(body_node, method_qn)
    
    def _extract_method(node: Node, class_qn: str):
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = _get_node_text(name_node, source)
        qn = f"{class_qn}.{name}"
        ordinal = _get_ordinal(qn, SymbolKind.METHOD.value)
        
        analysis.symbols.append(SymbolInfo(
            name=name, qualified_name=qn, kind=SymbolKind.METHOD,
            file_path=file_path, location=_make_location(node),
            ordinal=ordinal,
        ))
        
        body = node.child_by_field_name("body")
        if body:
            _extract_calls(body, qn)
            _extract_symbols(body, qn)
    
    def _extract_variable_decl(node: Node, parent_qn: str):
        for declarator in node.children:
            if declarator.type == "variable_declarator":
                name_node = declarator.child_by_field_name("name")
                value_node = declarator.child_by_field_name("value")
                
                if name_node and value_node:
                    name = _get_node_text(name_node, source)
                    qn = f"{parent_qn}.{name}" if parent_qn else name
                    
                    if value_node.type in ("arrow_function", "function_expression", "function"):
                        kind = SymbolKind.FUNCTION
                        ordinal = _get_ordinal(qn, kind.value)
                        analysis.symbols.append(SymbolInfo(
                            name=name, qualified_name=qn, kind=kind,
                            file_path=file_path, location=_make_location(node),
                            ordinal=ordinal,
                        ))
                        body = value_node.child_by_field_name("body")
                        if body:
                            _extract_calls(body, qn)
                            _extract_symbols(body, qn)
    
    def _extract_export(node: Node, parent_qn: str):
        for child in node.children:
            if child.type == "function_declaration":
                _extract_function(child, parent_qn)
            elif child.type in ("class_declaration", "abstract_class_declaration"):
                _extract_class(child, parent_qn)
            elif child.type in ("lexical_declaration", "variable_declaration"):
                _extract_variable_decl(child, parent_qn)
            elif child.type == "interface_declaration":
                _extract_interface(child, parent_qn)
            elif child.type == "enum_declaration":
                _extract_enum(child, parent_qn)
    
    def _extract_interface(node: Node, parent_qn: str):
        """Extract interface as a Class symbol (structural type)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = _get_node_text(name_node, source)
        qn = f"{parent_qn}.{name}" if parent_qn else name
        ordinal = _get_ordinal(qn, SymbolKind.CLASS.value)
        
        analysis.symbols.append(SymbolInfo(
            name=name, qualified_name=qn, kind=SymbolKind.CLASS,
            file_path=file_path, location=_make_location(node),
            ordinal=ordinal,
        ))
        
        # Extract extends for interfaces
        for c in node.children:
            if c.type == "extends_type_clause":
                for id_node in c.children:
                    base_name = _extract_type_name(id_node, source)
                    if base_name:
                        analysis.inheritance.append(InheritanceInfo(
                            class_name=name,
                            base_class_name=base_name,
                            file_path=file_path,
                        ))
        
        # Extract method signatures from interface body
        body = node.child_by_field_name("body")
        if body:
            for member in body.children:
                if member.type == "method_signature":
                    m_name_node = member.child_by_field_name("name")
                    if m_name_node:
                        m_name = _get_node_text(m_name_node, source)
                        m_qn = f"{qn}.{m_name}"
                        m_ord = _get_ordinal(m_qn, SymbolKind.METHOD.value)
                        analysis.symbols.append(SymbolInfo(
                            name=m_name, qualified_name=m_qn, kind=SymbolKind.METHOD,
                            file_path=file_path, location=_make_location(member),
                            ordinal=m_ord,
                        ))
    
    def _extract_enum(node: Node, parent_qn: str):
        """Extract enum as a Class symbol."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = _get_node_text(name_node, source)
        qn = f"{parent_qn}.{name}" if parent_qn else name
        ordinal = _get_ordinal(qn, SymbolKind.CLASS.value)
        
        analysis.symbols.append(SymbolInfo(
            name=name, qualified_name=qn, kind=SymbolKind.CLASS,
            file_path=file_path, location=_make_location(node),
            ordinal=ordinal,
        ))
    
    def _extract_import(node: Node):
        source_node = node.child_by_field_name("source")
        if not source_node:
            return
        
        module_name = _get_node_text(source_node, source).strip("'\"")
        imported_names = []
        is_default = False
        is_namespace = False
        
        for child in node.children:
            if child.type == "import_clause":
                for sub in child.children:
                    if sub.type == "identifier":
                        imported_names.append(_get_node_text(sub, source))
                        is_default = True
                    elif sub.type == "named_imports":
                        for spec in sub.children:
                            if spec.type == "import_specifier":
                                name_node = spec.child_by_field_name("name")
                                if name_node:
                                    imported_names.append(_get_node_text(name_node, source))
                    elif sub.type == "namespace_import":
                        for id_node in sub.children:
                            if id_node.type == "identifier":
                                imported_names.append(f"* as {_get_node_text(id_node, source)}")
                                is_namespace = True
        
        analysis.imports.append(ImportInfo(
            module_name=module_name,
            imported_names=imported_names,
            file_path=file_path,
            location=_make_location(node),
            is_default=is_default,
            is_namespace=is_namespace,
        ))
    
    def _extract_calls(node: Node, caller_qn: str):
        for child in node.children:
            if child.type == "call_expression":
                func_node = child.child_by_field_name("function")
                if func_node:
                    callee_name = _get_node_text(func_node, source)
                    analysis.calls.append(CallInfo(
                        caller_qualified_name=caller_qn,
                        callee_name=callee_name,
                        file_path=file_path,
                        location=_make_location(child),
                    ))
                    analysis.references.append(ReferenceInfo(
                        name=callee_name,
                        file_path=file_path,
                        location=_make_location(func_node),
                        status=ReferenceStatus.SYNTACTIC,
                        context_qualified_name=caller_qn,
                    ))
            elif child.type == "new_expression":
                ctor_node = child.child_by_field_name("constructor")
                if ctor_node:
                    callee_name = _get_node_text(ctor_node, source)
                    analysis.calls.append(CallInfo(
                        caller_qualified_name=caller_qn,
                        callee_name=callee_name,
                        file_path=file_path,
                        location=_make_location(child),
                    ))
                    analysis.references.append(ReferenceInfo(
                        name=callee_name,
                        file_path=file_path,
                        location=_make_location(ctor_node),
                        status=ReferenceStatus.SYNTACTIC,
                        context_qualified_name=caller_qn,
                    ))
            if child.type in ("statement_block", "if_statement", "for_statement",
                             "for_in_statement", "while_statement", "do_statement",
                             "switch_statement", "switch_body", "switch_case",
                             "switch_default", "try_statement", "catch_clause",
                             "finally_clause", "return_statement",
                             "expression_statement", "variable_declaration",
                             "lexical_declaration", "variable_declarator",
                             "assignment_expression", "augmented_assignment_expression",
                             "sequence_expression", "ternary_expression",
                             "binary_expression", "unary_expression",
                             "template_string", "template_substitution",
                             "array", "object", "pair", "spread_element",
                             "parenthesized_expression", "member_expression",
                             "subscript_expression", "arguments",
                             "call_expression", "new_expression",
                             "arrow_function", "yield_expression",
                             "await_expression", "as_expression",
                             "type_assertion", "non_null_expression",
                             "satisfies_expression", "jsx_element",
                             "jsx_self_closing_element", "jsx_attribute",
                             "jsx_expression"):
                _extract_calls(child, caller_qn)
    
    _extract_symbols(root_node)
    return analysis
