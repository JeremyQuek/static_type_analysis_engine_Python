# Python Static Type Analysis Engine

### 1.1 Motivation

Python has become one of the dominant programming languages for backend systems, artificial intelligence, machine learning, scientific computing, and cloud infrastructure, valued for its flexibility and rapid development cycle. Unlike statically typed languages, Python's type system is optional — developers can write programs without explicit type declarations or compile-time enforcement. While modern type annotation systems such as PEP 484 improve static analysis, adoption across open-source projects remains inconsistent, and many widely used libraries rely heavily on dynamic language features.

The consequence is a practical developer experience problem I encountered repeatedly while working with Python frameworks such as LangChain, FastAPI, and SQLAlchemy: objects are propagated through multiple layers of abstraction before their concrete runtime types become apparent, and existing editor tooling presents inferred types as isolated results with no explanation of how those conclusions were reached. Developers are left manually tracing through assignments, helper functions, and files to understand what a variable actually is.

### 1.2 Problem Statement

Developers frequently encounter variables whose runtime types cannot be determined from local context alone. This requires manually navigating source code, inspecting function definitions, and following assignment chains across multiple files — a process that is slow, error-prone, and particularly painful in large codebases built on abstraction-heavy frameworks.

Existing tools such as Pylance and mypy perform type inference but surface only the end result, not the semantic reasoning behind it. This leaves developers without the context needed to understand, verify, or debug the inferred type — especially in dynamic codebases where the type annotation coverage is incomplete.

### 1.3 Project Scope and Objectives

I proposed and built the **Python Static Type Analysis Engine**: a semantic analysis system that statically approximates the runtime type of Python variables by recursively tracing their semantic provenance throughout a project, and exposes the complete reasoning process as an explainable assignment trace within the editor.

My objectives were:

1. **Static semantic model construction**: parse Python source files into ASTs, build lexical scope trees, and construct persistent symbol tables that support arbitrary point-in-time symbol lookups.
2. **Recursive type analysis**: implement an interprocedural analysis engine that traces variable assignments and function calls across project files to approximate runtime types.
3. **Explainability**: produce a structured assignment trace alongside each inferred type, showing the exact chain of reasoning from the query site back to the type's origin.
4. **Editor integration**: integrate the engine as a live background service in Visual Studio Code, surfacing results on hover without requiring program execution.

---

## Section 2: System Design

### 2.1 System Overview

The Python Static Type Analysis Engine operates as a background semantic analysis service integrated into the development environment. Whenever source files are modified, the system incrementally parses the project and maintains a semantic model consisting of abstract syntax trees, lexical scope trees, symbol tables, and cross-file symbol relationships.

When a developer hovers over a variable, the system:

- resolves the corresponding symbol definition
- recursively traces its semantic provenance across assignments and function calls
- approximates the most likely runtime type
- presents an explainable assignment trace describing the inference process

No program execution or runtime instrumentation is required at any stage.

### 2.2 Core Output Model

Each inspected variable is represented as a structured semantic analysis result:

```
Variable:
    result

Inferred Type:
    AIMessage

Confidence:
    High

Assignment Trace:

main.py:42
result = agent.invoke(...)
↓
agent.py:61
return execute_chain(...)
↓
chain.py:118
return ChatOpenAI.invoke(...)
↓
chat_models.py:94
return AIMessage(...)

Analysis Status:
    RESOLVED
```

When precise inference is not possible — due to dynamic dispatch, missing annotations, or unsupported language features — the system reports a conservative approximation or `Unknown` rather than making an unsound assumption.

### 2.3 Architectural Design

The system is structured into three layers:

**Semantic Model Layer**: responsible for parsing source files and maintaining the persistent, incrementally updated representation of the project. This includes the AST builder, the Lexical Scope Tree (LST) constructor, symbol table management, and the cross-file import resolver.

**Analysis Engine Layer**: the core reasoning component. It takes a symbol query (file, line, column) as input, resolves the definition, and recursively traces the assignment and call graph to produce a typed inference result with a confidence level and assignment trace.

**Editor Integration Layer**: the VS Code extension that communicates with the analysis engine, requests analysis on hover events, and renders the structured output — inferred type, confidence, trace, and source links — within the editor UI.

### 2.4 Key Design Decisions

**Persistent scope tree over traversal-time symbol tables**: Traditional compiler symbol tables are constructed and discarded during a single sequential AST traversal. This is insufficient for IDE use cases, where type information must be available on demand for any location in any file. I addressed this by representing lexical scopes as a persistent tree — the Lexical Scope Tree (LST) — where each node owns the contiguous source interval over which it is valid. This allows arbitrary query locations to be mapped efficiently to the correct scope before symbol resolution begins.

```
main.py

Module Scope [1, 200]
│
├── Function foo() [10, 60]
│   ├── If Scope [20, 35]
│   └── For Scope [40, 55]
│
└── Class Bar [80, 180]
    └── Method baz() [95, 140]
```

**Conservative inference over unsound approximation**: Where dynamic language features — such as `getattr`, `eval`, or dynamically constructed class hierarchies — prevent reliable analysis, the system reports `Unknown` rather than a potentially incorrect type. I chose soundness-over-completeness as the guiding principle: a missing answer is less harmful than a wrong one.

**Leveraging the standard `ast` module**: Python exposes a complete parser and canonical AST through the standard library's `ast` module. I chose to build on this foundation rather than implement a custom parser, which would have constituted a substantial project in its own right and shifted focus away from the semantic analysis problem.

---

## Section 3: Implementation

### 3.1 Phase 1 — Static Semantic Analysis Infrastructure

Phase 1 focused on developing the semantic analysis engine for a single Python source file.

**Phase 1.1 — Symbol Resolution**

I began by building the foundation: parsing source files into ASTs using Python's `ast` module, constructing the Lexical Scope Tree from the AST, and populating per-scope symbol tables with variable definitions and their source locations. The key insight I implemented here is that each LST node stores the source interval `[start_line, end_line]` over which its scope is valid. Given a query location, I can walk the LST to find the innermost enclosing scope in O(depth) time, then perform symbol resolution by walking up the parent chain — accurately modelling Python's LEGB (Local, Enclosing, Global, Built-in) scoping rules.

**Phase 1.2 — Variable Assignment Tracing**

With symbol resolution in place, I implemented semantic provenance through variable assignments. The tracer follows a variable's definition backwards through reassignment chains, resolving aliases until it reaches a primitive value or explicit constructor call. For example:

```
x = 3
y = x
z = y
```

Produces the trace: `z → y → x → int`

Each step in the chain records its source location, forming the basis of the explainable assignment trace shown in the output model.

**Phase 1.4 — Control Flow Analysis**

I implemented conservative reasoning across branching execution paths. Where a variable may be assigned different types in different branches (e.g., different arms of an `if/else`), the engine reports a union type. Where a branch outcome cannot be statically determined, the engine defaults to `Unknown` for that path and unions across all possible outcomes.

**Phase 1.5 — User-Defined Object Analysis**

I extended the engine to resolve class constructors and infer instantiated object types. When the tracer encounters a call expression that resolves to a class definition, it infers the constructed type directly. Simple method return values are followed using the same interprocedural tracing mechanism developed in Phase 2.

**Phase 1.6 — Nested Scope Resolution**

I implemented full LEGB scope resolution, correctly handling shadowed variables, nested functions, and `nonlocal`/`global` declarations. The scope tree structure makes this straightforward: resolution walks up parent scope nodes until a matching symbol is found, with `global` declarations short-circuiting directly to the module scope.

The ingestion pipeline exemplifies event-driven architecture, where components communicate by reacting to change events rather than polling. Each source file modification triggers an incremental AST rebuild and partial scope tree update rather than a full reparse, keeping the semantic model continuously fresh at low cost.

### 3.2 Phase 2 — Recursive Interprocedural Analysis

Phase 2 generalised the engine beyond a single file.

**Phase 2.1 — Cross-File Symbol Resolution**

I built a module dependency graph by resolving import statements across the project. Each `import` or `from X import Y` statement is followed to its source file, and the imported symbol is resolved in the target module's scope tree. This allows the assignment tracer to follow function calls and variable references that originate in other files seamlessly.

**Phase 2.2 — Recursive Interprocedural Analysis**

The core contribution of Phase 2 is the recursive interprocedural tracer. When the engine encounters a function call, it resolves the callee's definition, traces into its body, and follows return statements back to their origins — recursively, across file boundaries. I implemented cycle detection to handle mutually recursive functions, marking a symbol as `Unknown` if the tracer revisits a node already present in the current analysis stack.

This is the mechanism that produces traces like:

```
main.py:42  result = agent.invoke(...)
↓
agent.py:61  return execute_chain(...)
↓
chain.py:118  return ChatOpenAI.invoke(...)
↓
chat_models.py:94  return AIMessage(...)
```

**Phase 2.3 — Performance and Incremental Analysis**

I implemented result caching keyed on (file, symbol, scope) and incremental AST updates that reparse only changed files on save. This reduced hover-response latency to a level suitable for interactive editor use, where a multi-hundred-millisecond delay would noticeably disrupt the development flow.

Static analysis of this kind relates to the broader concept of abstract interpretation in programming language theory — a framework for computing sound approximations of program behaviour over all possible inputs without execution. My conservative inference strategy, where dynamic constructs default to `Unknown` rather than an unsound guess, directly reflects the safety property that abstract interpretation formalises.

### 3.3 Phase 3 — Visual Studio Code Integration

I integrated the analysis engine into VS Code via the Language Server Protocol (LSP), implementing a language server that the extension communicates with over stdin/stdout. The server maintains the semantic model in the background, receives `textDocument/hover` requests from the editor, queries the analysis engine, and returns a formatted response containing the inferred type, confidence level, assignment trace, and source locations as clickable links.

The LSP is a well-established protocol that decouples language-specific analysis from editor-specific UI concerns, enabling the same engine to be integrated into other editors (e.g., Neovim, Emacs) with minimal additional work. Using LSP rather than a VS Code-specific extension API was a deliberate choice I made to maximise the portability of the engine.

---

## Chapter 4: Limitations

### **4.1 Type Mutation through Expressions**

The engine operates on the assumption that type mutations are caused by explicit assignment statements (`ast.Assign`, `ast.AugAssign`). This is sound for the vast majority of Python code, but Python's dynamic nature exposes a class of edge cases where a pure expression — with no assignment node in the AST — can nonetheless mutate a top-level type binding. I cannot detect these cases, and I think it is important to be precise about why.

**Namespace mutation via built-in dictionaries**: In Python, variables are keys in a dictionary. An expression like `globals().update({"x": "string"})` or direct manipulation of `sys.modules[__name__].__dict__` evaluates a function call that forcibly rebinds a top-level identifier. From the AST's perspective this is an `ast.Call` with no assignment target — structurally indistinguishable from any other innocuous method call. The engine has no way to identify that the callee is `globals()` without executing the program.

**Side-effecting built-in functions**: `setattr(sys.modules[__name__], 'x', 3.14)` rewrites the top-level binding of `x` as a side effect of a call expression. Similarly, `delattr()` can delete a binding entirely, causing subsequent references to raise `NameError`. Both are `ast.Call` nodes; neither has a syntactically visible assignment.

**`__class__` mutation**: An expression that assigns to the `__class__` attribute of a live object — whether directly or as a side effect inside a method call — swaps the object's type in place without changing the identifier that points to it. The analyzer's symbol table continues to record the original type, which is now incorrect.

**C-level memory manipulation**: Expressions using `ctypes.memmove()` or `gc.get_referents()` can overwrite object memory at the C level, converting an `int` structure into a `str` structure without any Python-level assignment. No AST-based analysis can detect this; it is invisible to the entire static analysis layer.

The practical impact of these limitations is modest. In ordinary application code and most open-source libraries, none of these patterns appear. They are predominantly found in testing infrastructure, metaprogramming frameworks, and low-level system code. For the motivating use case — understanding variable types in framework-heavy Python such as LangChain or FastAPI — the engine's assumption holds cleanly. I designed it to report `Unknown` conservatively whenever analysis reaches a boundary it cannot cross, which means the failure mode is a missing answer rather than a wrong one.
