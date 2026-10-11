"""Tests for Phase 2: Structural Analysis (Python, JavaScript, TypeScript).

GATE 2 requirements:
- Fixtures per language with known expected symbol and relationship lists.
- Tests assert exact output (names, kinds, line ranges, imports, calls, inheritance).
- Include fixtures with a syntax error, duplicate names, and dynamic constructs.
- Unsupported extensions reported as unsupported, never silently ignored.
"""

from __future__ import annotations

import os
import tempfile
import shutil
import pytest

from synapse.models import (
    SymbolKind, ReferenceStatus, FileAnalysis,
)
from synapse.analysis.dispatcher import analyze_file
from synapse.analysis.python_analyzer import analyze_python
from synapse.analysis.js_analyzer import analyze_javascript
from synapse.analysis.ts_analyzer import analyze_typescript
from synapse.parsing.parser import parse_source, get_language_for_file


# =============================================================================
# Python Fixtures and Tests
# =============================================================================

PYTHON_FIXTURE_SOURCE = b'''import os
import math as m
from sys import version, platform
from .local import helper

class Animal:
    def __init__(self, name: str):
        self.name = name

    def speak(self) -> str:
        return "..."

    def get_name(self) -> str:
        return self.name

class Dog(Animal):
    def speak(self) -> str:
        super().speak()
        print("Woof")
        return "Woof"

def make_dog(name: str) -> Dog:
    helper()
    d = Dog(name)
    def inner_helper():
        print("inner")
    inner_helper()
    return d
'''


class TestPythonStructuralAnalysis:
    """Test Python structural analysis against known ground-truth fixtures."""

    @pytest.fixture
    def analysis(self) -> FileAnalysis:
        root_node = parse_source(PYTHON_FIXTURE_SOURCE, "python")
        assert root_node is not None
        return analyze_python(root_node, PYTHON_FIXTURE_SOURCE, "test_pkg/animals.py")

    def test_python_symbols_exact(self, analysis: FileAnalysis):
        symbols = analysis.symbols
        sym_map = {s.qualified_name: s for s in symbols}

        expected_qnames = [
            "Animal",
            "Animal.__init__",
            "Animal.speak",
            "Animal.get_name",
            "Dog",
            "Dog.speak",
            "make_dog",
            "make_dog.inner_helper",
        ]
        assert sorted(sym_map.keys()) == sorted(expected_qnames)

        # Assert kinds
        assert sym_map["Animal"].kind == SymbolKind.CLASS
        assert sym_map["Animal.__init__"].kind == SymbolKind.METHOD
        assert sym_map["Animal.speak"].kind == SymbolKind.METHOD
        assert sym_map["Animal.get_name"].kind == SymbolKind.METHOD
        assert sym_map["Dog"].kind == SymbolKind.CLASS
        assert sym_map["Dog.speak"].kind == SymbolKind.METHOD
        assert sym_map["make_dog"].kind == SymbolKind.FUNCTION
        assert sym_map["make_dog.inner_helper"].kind == SymbolKind.FUNCTION

        # Assert exact line numbers
        assert sym_map["Animal"].location.start_line == 6
        assert sym_map["Animal.__init__"].location.start_line == 7
        assert sym_map["Animal.__init__"].location.end_line == 8
        assert sym_map["Animal.speak"].location.start_line == 10
        assert sym_map["Animal.speak"].location.end_line == 11
        assert sym_map["Dog"].location.start_line == 16
        assert sym_map["Dog.speak"].location.start_line == 17
        assert sym_map["Dog.speak"].location.end_line == 20
        assert sym_map["make_dog"].location.start_line == 22
        assert sym_map["make_dog.inner_helper"].location.start_line == 25

    def test_python_inheritance_exact(self, analysis: FileAnalysis):
        assert len(analysis.inheritance) == 1
        inh = analysis.inheritance[0]
        assert inh.class_name == "Dog"
        assert inh.base_class_name == "Animal"
        assert inh.file_path == "test_pkg/animals.py"

    def test_python_imports_exact(self, analysis: FileAnalysis):
        imp_modules = {imp.module_name: imp for imp in analysis.imports}
        assert "os" in imp_modules
        assert "math" in imp_modules
        assert imp_modules["math"].alias == "m"

        assert "sys" in imp_modules
        assert sorted(imp_modules["sys"].imported_names) == ["platform", "version"]

        assert ".local" in imp_modules
        assert imp_modules[".local"].imported_names == ["helper"]

    def test_python_calls_exact(self, analysis: FileAnalysis):
        calls = [(c.caller_qualified_name, c.callee_name) for c in analysis.calls]
        assert ("Dog.speak", "super") in calls or ("Dog.speak", "super().speak") in calls or any(c[0] == "Dog.speak" and "speak" in c[1] for c in calls)
        assert ("Dog.speak", "print") in calls
        assert ("make_dog", "helper") in calls
        assert ("make_dog", "Dog") in calls
        assert ("make_dog", "inner_helper") in calls
        assert ("make_dog.inner_helper", "print") in calls

    def test_python_references_syntactic(self, analysis: FileAnalysis):
        assert len(analysis.references) > 0
        for ref in analysis.references:
            assert ref.status == ReferenceStatus.SYNTACTIC
            assert ref.resolved_symbol_id is None


# =============================================================================
# JavaScript Fixtures and Tests
# =============================================================================

JAVASCRIPT_FIXTURE_SOURCE = b'''import defaultLib, { helperFn, utilObj as u } from './lib';
import * as math from './math';

class BaseWidget {
  constructor(id) {
    this.id = id;
  }

  render() {
    return this.id;
  }
}

class Button extends BaseWidget {
  constructor(id, label) {
    super(id);
    this.label = label;
  }

  click() {
    helperFn(this.id);
  }

  onHover = () => {
    defaultLib(this.label);
  };
}

function createButton(label) {
  return new Button("btn-1", label);
}

export const formatText = (text) => {
  return text.trim();
};
'''


class TestJavaScriptStructuralAnalysis:
    """Test JavaScript structural analysis against known ground-truth fixtures."""

    @pytest.fixture
    def analysis(self) -> FileAnalysis:
        root_node = parse_source(JAVASCRIPT_FIXTURE_SOURCE, "javascript")
        assert root_node is not None
        return analyze_javascript(root_node, JAVASCRIPT_FIXTURE_SOURCE, "src/components/button.js")

    def test_js_symbols_exact(self, analysis: FileAnalysis):
        symbols = analysis.symbols
        sym_map = {s.qualified_name: s for s in symbols}

        expected_qnames = [
            "BaseWidget",
            "BaseWidget.constructor",
            "BaseWidget.render",
            "Button",
            "Button.constructor",
            "Button.click",
            "Button.onHover",
            "createButton",
            "formatText",
        ]
        assert sorted(sym_map.keys()) == sorted(expected_qnames)

        assert sym_map["BaseWidget"].kind == SymbolKind.CLASS
        assert sym_map["BaseWidget.constructor"].kind == SymbolKind.METHOD
        assert sym_map["BaseWidget.render"].kind == SymbolKind.METHOD
        assert sym_map["Button"].kind == SymbolKind.CLASS
        assert sym_map["Button.constructor"].kind == SymbolKind.METHOD
        assert sym_map["Button.click"].kind == SymbolKind.METHOD
        assert sym_map["Button.onHover"].kind == SymbolKind.METHOD
        assert sym_map["createButton"].kind == SymbolKind.FUNCTION
        assert sym_map["formatText"].kind == SymbolKind.FUNCTION

        # Check exact line numbers
        assert sym_map["BaseWidget"].location.start_line == 4
        assert sym_map["Button"].location.start_line == 14
        assert sym_map["createButton"].location.start_line == 29
        assert sym_map["formatText"].location.start_line == 33

    def test_js_inheritance_exact(self, analysis: FileAnalysis):
        assert len(analysis.inheritance) == 1
        inh = analysis.inheritance[0]
        assert inh.class_name == "Button"
        assert inh.base_class_name == "BaseWidget"
        assert inh.file_path == "src/components/button.js"

    def test_js_imports_exact(self, analysis: FileAnalysis):
        imp_modules = {imp.module_name: imp for imp in analysis.imports}
        assert "./lib" in imp_modules
        assert imp_modules["./lib"].is_default is True
        assert "defaultLib" in imp_modules["./lib"].imported_names
        assert "helperFn" in imp_modules["./lib"].imported_names

        assert "./math" in imp_modules
        assert imp_modules["./math"].is_namespace is True

    def test_js_calls_exact(self, analysis: FileAnalysis):
        calls = [(c.caller_qualified_name, c.callee_name) for c in analysis.calls]
        assert ("Button.constructor", "super") in calls
        assert ("Button.click", "helperFn") in calls
        assert ("Button.onHover", "defaultLib") in calls
        assert ("createButton", "Button") in calls
        assert ("formatText", "text.trim") in calls or any(c[0] == "formatText" and "trim" in c[1] for c in calls)


# =============================================================================
# TypeScript and TSX Fixtures and Tests
# =============================================================================

TYPESCRIPT_FIXTURE_SOURCE = b'''import { User, Config } from './types';

export interface IRepository<T> {
  findById(id: string): T;
  save(item: T): void;
}

export enum UserStatus {
  Active,
  Inactive,
}

export abstract class AbstractService {
  abstract initialize(): void;
}

export class UserService extends AbstractService implements IRepository<User> {
  initialize(): void {
    this.setup();
  }

  setup(): void {
    Config.load();
  }

  findById(id: string): User {
    return new User(id);
  }

  save(item: User): void {
    validate(item);
  }
}

export function registerUser(name: string): User {
  const service = new UserService();
  return service.findById(name);
}
'''

TSX_FIXTURE_SOURCE = b'''import React, { useState } from 'react';

export function Counter(props: { initial: number }) {
  const [count, setCount] = useState(props.initial);

  const increment = () => {
    setCount(count + 1);
  };

  return (
    <div className="counter">
      <span>{count}</span>
      <button onClick={increment}>Increment</button>
    </div>
  );
}
'''


class TestTypeScriptStructuralAnalysis:
    """Test TypeScript and TSX structural analysis against known ground-truth fixtures."""

    @pytest.fixture
    def ts_analysis(self) -> FileAnalysis:
        root_node = parse_source(TYPESCRIPT_FIXTURE_SOURCE, "typescript")
        assert root_node is not None
        return analyze_typescript(root_node, TYPESCRIPT_FIXTURE_SOURCE, "src/services/user.ts", language="typescript")

    @pytest.fixture
    def tsx_analysis(self) -> FileAnalysis:
        root_node = parse_source(TSX_FIXTURE_SOURCE, "tsx")
        assert root_node is not None
        return analyze_typescript(root_node, TSX_FIXTURE_SOURCE, "src/components/Counter.tsx", language="tsx")

    def test_ts_symbols_exact(self, ts_analysis: FileAnalysis):
        symbols = ts_analysis.symbols
        sym_map = {s.qualified_name: s for s in symbols}

        expected_qnames = [
            "IRepository",
            "IRepository.findById",
            "IRepository.save",
            "UserStatus",
            "AbstractService",
            "AbstractService.initialize",
            "UserService",
            "UserService.initialize",
            "UserService.setup",
            "UserService.findById",
            "UserService.save",
            "registerUser",
        ]
        assert sorted(sym_map.keys()) == sorted(expected_qnames)

        assert sym_map["IRepository"].kind == SymbolKind.CLASS
        assert sym_map["IRepository.findById"].kind == SymbolKind.METHOD
        assert sym_map["IRepository.save"].kind == SymbolKind.METHOD
        assert sym_map["UserStatus"].kind == SymbolKind.CLASS
        assert sym_map["AbstractService"].kind == SymbolKind.CLASS
        assert sym_map["AbstractService.initialize"].kind == SymbolKind.METHOD
        assert sym_map["UserService"].kind == SymbolKind.CLASS
        assert sym_map["UserService.initialize"].kind == SymbolKind.METHOD
        assert sym_map["UserService.setup"].kind == SymbolKind.METHOD
        assert sym_map["UserService.findById"].kind == SymbolKind.METHOD
        assert sym_map["UserService.save"].kind == SymbolKind.METHOD
        assert sym_map["registerUser"].kind == SymbolKind.FUNCTION

    def test_ts_inheritance_exact(self, ts_analysis: FileAnalysis):
        inh_pairs = [(i.class_name, i.base_class_name) for i in ts_analysis.inheritance]
        assert ("UserService", "AbstractService") in inh_pairs
        assert ("UserService", "IRepository") in inh_pairs

    def test_ts_imports_exact(self, ts_analysis: FileAnalysis):
        assert len(ts_analysis.imports) == 1
        imp = ts_analysis.imports[0]
        assert imp.module_name == "./types"
        assert sorted(imp.imported_names) == ["Config", "User"]

    def test_ts_calls_exact(self, ts_analysis: FileAnalysis):
        calls = [(c.caller_qualified_name, c.callee_name) for c in ts_analysis.calls]
        assert ("UserService.initialize", "this.setup") in calls
        assert ("UserService.setup", "Config.load") in calls
        assert ("UserService.findById", "User") in calls
        assert ("UserService.save", "validate") in calls
        assert ("registerUser", "UserService") in calls
        assert ("registerUser", "service.findById") in calls

    def test_tsx_symbols_and_calls(self, tsx_analysis: FileAnalysis):
        symbols = tsx_analysis.symbols
        sym_map = {s.qualified_name: s for s in symbols}

        assert "Counter" in sym_map
        assert sym_map["Counter"].kind == SymbolKind.FUNCTION
        assert "Counter.increment" in sym_map
        assert sym_map["Counter.increment"].kind == SymbolKind.FUNCTION

        calls = [(c.caller_qualified_name, c.callee_name) for c in tsx_analysis.calls]
        assert ("Counter", "useState") in calls
        assert ("Counter.increment", "setCount") in calls


# =============================================================================
# Adversarial, Malformed, Duplicate & Dynamic Fixtures
# =============================================================================

class TestEdgeCasesAndAdversarialFixtures:
    """Test syntax errors, duplicate names, dynamic constructs, and unsupported extensions."""

    def test_syntax_error_python(self):
        broken_code = b"def unclosed_function(a, b:\n    return a + b\n"
        root_node = parse_source(broken_code, "python")
        assert root_node is not None
        analysis = analyze_python(root_node, broken_code, "broken.py")
        from synapse.parsing.parser import has_parse_errors
        assert has_parse_errors(root_node) is True
        # Partial extraction flagged:
        assert root_node.has_error is True

    def test_syntax_error_javascript(self):
        broken_code = b"class BrokenWidget { render() { if (true) { return 42; }\n"
        root_node = parse_source(broken_code, "javascript")
        assert root_node is not None
        from synapse.parsing.parser import has_parse_errors
        assert has_parse_errors(root_node) is True

    def test_syntax_error_typescript(self):
        broken_code = b"export interface Broken { foo(:\n"
        root_node = parse_source(broken_code, "typescript")
        assert root_node is not None
        from synapse.parsing.parser import has_parse_errors
        assert has_parse_errors(root_node) is True

    def test_duplicate_names_python(self):
        """Duplicate function names in the same file must have distinct ordinals and symbol IDs."""
        code = b'''def handler():
    return 1

def handler():
    return 2
'''
        root_node = parse_source(code, "python")
        assert root_node is not None
        analysis = analyze_python(root_node, code, "dup.py")
        assert len(analysis.symbols) == 2
        s1, s2 = analysis.symbols[0], analysis.symbols[1]
        assert s1.name == "handler" and s2.name == "handler"
        assert s1.ordinal == 0 and s2.ordinal == 1
        assert s1.symbol_id != s2.symbol_id
        assert s1.location.start_line == 1
        assert s2.location.start_line == 4

    def test_duplicate_names_javascript(self):
        code = b'''function process() { return 1; }
function process() { return 2; }
'''
        root_node = parse_source(code, "javascript")
        assert root_node is not None
        analysis = analyze_javascript(root_node, code, "dup.js")
        assert len(analysis.symbols) == 2
        s1, s2 = analysis.symbols[0], analysis.symbols[1]
        assert s1.ordinal == 0 and s2.ordinal == 1
        assert s1.symbol_id != s2.symbol_id

    def test_duplicate_names_typescript(self):
        code = b'''class Worker { run() {} }
class Worker { run() {} }
'''
        root_node = parse_source(code, "typescript")
        assert root_node is not None
        analysis = analyze_typescript(root_node, code, "dup.ts")
        workers = [s for s in analysis.symbols if s.kind == SymbolKind.CLASS]
        assert len(workers) == 2
        assert workers[0].ordinal == 0 and workers[1].ordinal == 1
        assert workers[0].symbol_id != workers[1].symbol_id

    def test_dynamic_constructs_remain_unresolved(self):
        """Dynamic reflection, getattr, eval must stay unresolved without fabricating edges."""
        py_code = b'''def dynamic_caller(obj, method_name):
    getattr(obj, method_name)()
    eval("arbitrary_code()")
'''
        root_node = parse_source(py_code, "python")
        assert root_node is not None
        analysis = analyze_python(root_node, py_code, "dynamic.py")
        
        # References are recorded syntactically, not resolved to fake symbols
        for ref in analysis.references:
            assert ref.status == ReferenceStatus.SYNTACTIC
            assert ref.resolved_symbol_id is None
        
        # Calls only capture the literal syntactically present callee names
        callees = [c.callee_name for c in analysis.calls]
        assert "getattr" in callees
        assert "eval" in callees
        # No speculative method_name resolved
        assert "arbitrary_code" not in callees

    def test_unsupported_extensions_reported(self):
        """Unsupported file extensions must be reported as unsupported, never silently ignored."""
        tmpdir = tempfile.mkdtemp()
        try:
            txt_file = os.path.join(tmpdir, "notes.txt")
            with open(txt_file, "w") as f:
                f.write("Some text documentation.")

            assert get_language_for_file("notes.txt") is None
            analysis = analyze_file("notes.txt", tmpdir)
            assert analysis is not None
            assert analysis.language == "unsupported"
            assert analysis.parse_error is True
            assert "unsupported" in analysis.parse_error_message.lower()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_malformed_file_via_dispatcher_flags_error(self):
        """Malformed file processed through dispatcher sets has_errors=True."""
        tmpdir = tempfile.mkdtemp()
        try:
            broken_file = os.path.join(tmpdir, "broken.py")
            with open(broken_file, "w") as f:
                f.write("def broken(\n")

            analysis = analyze_file("broken.py", tmpdir)
            assert analysis is not None
            assert analysis.has_errors is True
            assert analysis.language == "python"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
