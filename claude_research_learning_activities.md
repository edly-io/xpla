# Innovating beyond SCORM and LTI: next-generation learning standards for executable content

**No single successor to SCORM has emerged, but a constellation of complementary standards—xAPI, cmi5, and LTI 1.3—now addresses its core limitations.** The most significant gap remains standardized support for sandboxed backend code execution within learning units. While containerized execution technologies have matured through platforms like JupyterHub and Judge0, no formal specification yet defines how executable coding content should be packaged, executed, and graded interoperably. Academic research from ITiCSE and SIGCSE communities has produced the Smart Learning Content architecture and SPLICE initiatives, which represent the closest approximations to new learning unit formats with execution capabilities.

## The post-SCORM standards landscape has fragmented by design

SCORM's limitations—browser-only execution, static content, tight LMS coupling, limited tracking vocabulary—spawned three major successor efforts rather than a single replacement. **xAPI** (now IEEE 9274.1.1-2023) provides universal learning tracking through actor-verb-object statements stored in Learning Record Stores, enabling tracking across mobile apps, simulators, IoT devices, and real-world activities. **cmi5** bridges SCORM's structure with xAPI's flexibility, critically introducing Assignable Units that can be hosted anywhere—not just on LMS servers—enabling Content-as-a-Service models and mobile app launch. **LTI 1.3** modernized tool integration with OAuth 2.0 security, enabling external tools to execute arbitrary server-side code while passing grades back to the LMS.

The ADL Initiative's **Total Learning Architecture (TLA)**, currently under IEEE study group evaluation, attempts to unify these pieces into a comprehensive framework with four data pillars: learning experience data (xAPI), learning activity metadata (IEEE P2881), competency data (IEEE 1484.20.1 RCD), and enterprise learner records. TLA's reference implementation uses Docker-containerized microservices and Kafka-based messaging, but this addresses infrastructure architecture rather than executable content specification.

## Academic research has focused on interoperability rather than execution standards

The most influential academic work on next-generation learning formats comes from the **ITiCSE 2014 Working Group** led by Peter Brusilovsky, Stephen Edwards, and colleagues. Their "Smart Learning Content" (SLC) architecture proposed a five-level integration framework for interactive learning objects—visualizations, simulations, web-based programming environments—with content metadata standards for describing pedagogical characteristics and difficulty. Unlike SCORM's static packaging, SLC decouples content from delivery platforms and introduces concept-level metadata for personalization.

This foundational research directly influenced the **ACOS Server** project (Karavirta, Ihantola, Sirkiä), which demonstrated service-oriented interoperability in practice. ACOS supports multiple communication protocols simultaneously—LTI, A+ protocol (a lightweight LTI alternative), and ADAPT2 protocol for adaptive learning—allowing content developers to create protocol-agnostic learning activities. The server handles protocol negotiation, enabling single content deployments across institutional boundaries without modification.

The **SPLICE (Standards, Protocols, and Learning Infrastructure for Computing Education)** community, active through SIGCSE workshops since 2019, has produced ongoing research on executable content. Notable contributions include Runestone's executable Python/Java/SQL examples with LTI integration, PrairieLearn's arbitrary code execution during question generation and grading, and cross-institutional content sharing between OpenDSA and ACOS platforms.

| Research Initiative | Year | Key Innovation | Current Status |
|---------------------|------|----------------|----------------|
| Smart Learning Content Architecture | 2014 | Five-level integration framework, concept metadata | Foundational; influenced ACOS, SPLICE |
| ACOS Server | 2013-2017 | Protocol-agnostic content delivery | Active open-source; OpenDSA integration |
| ROLE Framework | 2011 | Widget-based PLEs, inter-widget communication | EU project completed; concepts adopted |
| SPLICE Community | 2019-present | Executable CS content, cross-platform sharing | Ongoing SIGCSE/ITiCSE workshops |
| NGDLE Framework | 2015 | Federated "confederation" architecture | EDUCAUSE guiding framework |

## Containerized and sandboxed execution has matured through platform implementations

Secure backend code execution in learning contexts relies primarily on container isolation, with several battle-tested approaches. **CodeJail**, Open edX's production solution, uses AppArmor for Linux-based security enforcement with ephemeral read-only execution directories and setrlimit constraints on CPU/memory. The two-layer architecture separates subprocess management from Python-specific execution, though it requires careful AppArmor configuration to be secure.

**JupyterHub with LTI Authenticator** represents the most widely deployed university solution. The `jupyterhub-ltiauthenticator` package supports LTI 1.1 and 1.3, converting JupyterHub into an LTI Tool Provider tested with Canvas, Moodle, Blackboard, and Open edX. Combined with Kubernetes orchestration (Zero to JupyterHub), each student receives an isolated container environment. **nbgrader** adds assignment distribution and autograding, though it runs student code with instructor permissions and requires external sandboxing for security.

**Judge0** provides open-source containerized execution via RESTful API, supporting **60+ programming languages** with configurable time/memory limits and network isolation. Originally built for competitive programming, it's increasingly adopted for e-learning code execution. **E2B** represents the cutting edge—using Firecracker microVMs (the same technology as AWS Lambda) to achieve sub-200ms sandbox startup with complete isolation between instances.

Browser-based execution through WebAssembly has emerged as a powerful complement. **Pyodide** compiles CPython to WebAssembly, running NumPy, Pandas, and scikit-learn entirely client-side—enabling **JupyterLite**, a fully browser-based Jupyter environment requiring no server infrastructure. Performance is 3-5x slower than native Python, but zero-installation accessibility makes it compelling for educational contexts where server resources are constrained.

## No standardized format exists for packaging executable coding exercises

This represents the most significant finding: **the e-learning industry lacks a SCORM-equivalent specification for coding exercises**. Each platform uses proprietary formats for specifying test cases, execution environments, grading criteria, and feedback mechanisms. CodeGrade, Codio, Gradescope, and Artemis each define their own exercise structures, creating vendor lock-in that impedes content portability.

**Artemis** (TU Munich, MIT license) demonstrates what a comprehensive solution looks like—integrated version control (LocalVC), continuous integration (LocalCI), Docker-based build agents, and support for Java, Python, C, Haskell, Kotlin, OCaml, Swift, VHDL, and Assembler. Its Ares framework simplifies test creation while preventing cheating, and EduTelligence integration adds AI-powered tutoring (Iris) and automated assessment (Athena). With deployment at 15+ universities and **694 GitHub stars**, it represents the most mature open-source option, though it remains a platform rather than a portable content standard.

The **Open edX XBlock system** provides modular extensibility—XBlocks are "miniature web applications" with state, views, and handlers that can integrate external execution services. Community implementations include Jupyter Graded XBlocks using Docker + nbgrader, Monaco + Judge0 integrations for multi-language assessments, and AI-powered feedback XBlocks. However, XBlocks use Open edX-specific APIs incompatible with SCORM/xAPI without additional wrappers.

## cmi5 provides the most promising foundation for executable content standards

Among existing specifications, **cmi5's Assignable Unit (AU) architecture** best accommodates executable content. AUs can reference remote URLs, enabling server-side content generation and Content-as-a-Service models. The specification supports mobile app launch without browser requirements, RESTful communication instead of JavaScript APIs, and xAPI extensions for arbitrary data capture. cmi5's IEEE standardization (P9274.3.1) is in progress, with ADL's CATAPULT project providing conformance test suites.

However, cmi5 defines communication protocols rather than execution environments. A standardized approach to executable learning content would need to extend cmi5 with:

- **Container specification**: Docker-compatible image format for exercise environments
- **Resource constraints**: CPU, memory, network, and timeout parameters
- **Test case format**: Input/output specifications, validation criteria, partial credit rules
- **Grading hooks**: Standard interfaces for autograder integration
- **xAPI profile for programming**: Verbs for compiled, debugged, tested, committed, syntaxError

The **xAPI Profile for Self-Regulated Learning** (IEEE Access 2018) demonstrates how domain-specific profiles can extend xAPI's vocabulary, and a similar "xAPI Profile for Programming Education" could standardize tracking of code compilation, debugging sessions, test failures, and commit history.

## Hybrid architectures combine server containers with browser-based fallback

The most robust implementations combine multiple execution approaches. **BinderHub** builds Docker images from Git repositories using repo2docker, deploys via Kubernetes, and provides browser access through JupyterHub—enabling one-click reproducible environments for any repository. UC Berkeley uses this for interactive data science textbooks.

Browser-based technologies provide resilience when server resources are unavailable. **StackBlitz WebContainers** run full Node.js environments via WebAssembly, enabling npm package installation and dev server execution entirely client-side. Combined with Pyodide for Python, organizations can provide interactive coding without provisioning infrastructure.

The **EDUCAUSE NGDLE (Next Generation Digital Learning Environment) framework** provides architectural guidance for these federated systems—advocating a "confederation of IT systems" using mash-up models with interoperable components. Implementation requires LTI for app launch, QTI for assessments, Common Cartridge for content packaging, Caliper/xAPI for analytics, OneRoster for enrollment data, and emerging standards for learner profiles and competencies.

## Conclusion: executable learning content standards remain an open problem

The post-SCORM landscape has successfully addressed tracking (xAPI), LMS integration (cmi5, LTI 1.3), and analytics (Caliper), but **executable content packaging remains unstandardized**. Academic initiatives like Smart Learning Content and SPLICE have proposed frameworks without achieving specification-level formalization. Platform implementations demonstrate mature containerization (JupyterHub, Judge0, E2B) and browser-based execution (Pyodide, WebContainers), but each uses proprietary exercise formats.

Three developments would advance the field: an **xAPI Profile for Programming Education** defining standard verbs for coding activities; a **Coding Exercise Interchange Format** (JSON-based) specifying test cases, environment requirements, and grading criteria; and a **Container Specification for Learning** extending cmi5 AUs with execution environment requirements. The CS education community, through venues like SIGCSE, ITiCSE, and the SPLICE working group, is best positioned to drive this standardization—building on the Smart Learning Content architecture and ACOS protocol-agnostic approach to create truly portable, executable learning units.