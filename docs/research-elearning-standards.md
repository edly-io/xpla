# E-Learning Standards Research

A summary of existing standards and projects related to interactive learning activities, with focus on approaches that improve upon SCORM and LTI.

## Established Standards

### SCORM (Sharable Content Object Reference Model)

The dominant e-learning standard since 2001, developed by ADL (Advanced Distributed Learning).

**How it works:**
- Content packaged as ZIP with `imsmanifest.xml`
- Runs in browser iframe, communicates with LMS via JavaScript API
- Tracks completion, scores, time spent, bookmarks

**Limitations:**
- No meaningful updates since SCORM 2004
- Browser-only, same-origin requirement
- No mobile/offline support
- Heavy runtime tracking limits scalability
- Black-box content - LMS cannot inspect or manipulate

**Sources:**
- [SCORM vs xAPI comparison](https://xapi.com/scorm-vs-the-experience-api-xapi/)
- [Valamis SCORM guide](https://www.valamis.com/hub/xapi)

---

### xAPI / Experience API (Tin Can API)

SCORM successor developed by Rustici Software for ADL, released 2013. Now IEEE-stewarded (version 2.0, October 2023).

**How it works:**
- Learning events recorded as "Actor-Verb-Object" statements
- Statements sent to a Learning Record Store (LRS) via REST API
- Example: `"John completed Quiz 1 with score 85%"`

**Key improvements over SCORM:**
- Track learning anywhere (mobile, offline, real-world, simulations)
- Not tied to LMS - any system can send statements
- Richer data model for analytics
- Content can be hosted anywhere

**Challenges:**
- More complex to implement
- Requires separate LRS infrastructure
- Many LMS still don't support it

**Sources:**
- [xAPI Overview](https://xapi.com/overview/)
- [xAPI Specification](https://xapi.com/scorm-vs-the-experience-api-xapi/)

---

### cmi5

An xAPI profile that combines SCORM's LMS integration with xAPI's flexibility. Originated from AICC, now maintained by ADL.

**How it works:**
- Content launched from LMS with session credentials
- Uses xAPI for tracking, but with standardized launch protocol
- Course structure defined in `cmi5.xml` manifest

**Key features:**
- Content can be hosted anywhere (not same-origin like SCORM)
- Session-based handshake with expiring credentials
- Standardized completion/pass/fail semantics
- Mobile-friendly

**Adoption:** Still limited - not all LMS support it yet.

**Sources:**
- [cmi5 Overview](https://xapi.com/cmi5/)
- [cmi5 vs SCORM vs xAPI](https://xapi.com/cmi5/comparison-of-scorm-xapi-and-cmi5/)
- [Easygenerator cmi5 guide](https://www.easygenerator.com/en/blog/results-tracking/cmi5-what-it-is-and-why-you-need-it/)

---

### LTI (Learning Tools Interoperability)

1EdTech standard for integrating external tools into an LMS. Currently at version 1.3 with "LTI Advantage" extensions.

**How it works:**
- LMS launches external tool via authenticated HTTP POST
- Tool runs on its own server, returns content to iframe
- Grade passback via Assignment and Grade Services

**LTI 1.3 / Advantage improvements:**
- Security: OAuth 2.0, OpenID Connect, JWT (replaces OAuth 1.0a signing)
- Deep Linking: tools can return content to embed in courses
- Names and Roles: secure roster access
- Assignment and Grade Services: bidirectional grade sync

**Key distinction:** LTI is for *tool integration*, not content packaging. Tools have their own backends but aren't sandboxed or capability-controlled.

**Sources:**
- [1EdTech LTI](https://www.1edtech.org/standards/lti)
- [LTI Advantage Overview](https://www.imsglobal.org/lti-advantage-overview)
- [LTI 1.3 Specification](https://www.imsglobal.org/spec/lti/v1p3)

---

### Common Cartridge

1EdTech packaging format for course content interchange between LMS platforms.

**How it works:**
- ZIP file with XML manifest
- Contains static content, assessments (QTI), discussion topics, LTI links
- LMS imports and renders content natively - no runtime API

**Key differences from SCORM:**

| Aspect | SCORM | Common Cartridge |
|--------|-------|------------------|
| Philosophy | Self-paced CBT | Collaborative instruction |
| Content model | Black-box | Transparent, LMS can manipulate |
| Assessments | Opaque | Native QTI, reusable questions |
| Runtime | Heavy JS API | None - import only |

**What's inside a cartridge:**
1. Manifest (organization, metadata, authorization)
2. Static content (HTML, images, PDFs, videos, or URLs)
3. Assessments (QTI format)
4. Discussion topics (pre-populated forums)
5. LTI links (external tools)
6. Academic alignments (curriculum mappings)

**Sources:**
- [Common Cartridge FAQ](https://www.imsglobal.org/cc/ccfaqs.html)
- [Edlink Common Cartridge guide](https://ed.link/community/common-cartridge/)

---

### QTI (Question & Test Interoperability)

XML format for assessment items and tests. Currently at version 3.0.

**23 interaction types including:**
- Choice (single/multiple select)
- Text entry, extended text
- Matching, ordering, hotspot
- Gap-fill, drag-and-drop
- Drawing, file upload
- Media interactions
- Portable Custom Interactions (PCI) - extensible

**XML structure:**
```xml
<qti-assessment-item identifier="q1" title="Example">
  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="identifier">
    <qti-correct-response>
      <qti-value>correct_id</qti-value>
    </qti-correct-response>
  </qti-response-declaration>

  <qti-outcome-declaration identifier="SCORE" cardinality="single" base-type="float"/>

  <qti-item-body>
    <p>Question text here</p>
    <qti-choice-interaction response-identifier="RESPONSE" max-choices="1">
      <qti-simple-choice identifier="a">Option A</qti-simple-choice>
      <qti-simple-choice identifier="correct_id">Option B</qti-simple-choice>
    </qti-choice-interaction>
  </qti-item-body>

  <qti-response-processing template="match_correct"/>
</qti-assessment-item>
```

**Scoring:** Declarative rules compare responses to correct answers. Supports partial credit and custom logic.

**Accessibility:** ARIA, SSML (text-to-speech), alternative content, Personal Needs Profiles.

**Sources:**
- [QTI 3.0 Implementation Guide](https://www.imsglobal.org/spec/qti/v3p0/impl)

---

## Open Source Projects

### H5P

MIT-licensed framework for interactive HTML5 content.

**Features:**
- 50+ content types (interactive videos, quizzes, simulations, games)
- Visual authoring - no programming required
- Native plugins for Moodle, WordPress, Drupal
- LTI integration for other platforms
- Mobile-friendly, responsive

**Limitations:**
- Better for bite-sized activities than full courses
- Client-side only - no backend logic

**Tools:**
- [h5p.org](https://h5p.org/) - open source community
- [h5p.com](https://h5p.com/) - commercial hosting
- [Lumi](https://lumi.education/en/) - desktop editor

**Sources:**
- [H5P Content Types](https://h5p.org/content-types-and-applications)
- [H5P in Moodle](https://docs.moodle.org/501/en/H5P)

---

### Open edX XBlocks

Component architecture for edX courseware.

**How it works:**
- XBlocks are "miniature web applications" with state, views, handlers
- Python-based, run within Open edX Django application
- Can represent anything from a paragraph to an entire course
- Any web app can be an XBlock runtime by implementing the API

**Examples:** AI-evaluated coding exercises, interactive timelines, flashcards, simulations.

**Limitations:**
- Tied to Open edX runtime (not portable)
- Not sandboxed (code has Django-level access)
- No capability manifest

**Sources:**
- [XBlock GitHub](https://github.com/openedx/XBlock)
- [XBlock Tutorial](https://docs.openedx.org/projects/xblock/en/latest/xblock-tutorial/overview/introduction.html)
- [Appsembler XBlocks guide](https://appsembler.com/blog/xblocks-plugins-for-open-edx/)

---

### Open Source Learning Record Stores

**Learning Locker**
- One of the first open source LRS (2013)
- [GitHub](https://github.com/LearningLocker/learninglocker)

**SQL LRS**
- Apache 2.0 license, Docker-ready
- SQL-based for BI tool integration
- [sqllrs.com](https://www.sqllrs.com/)

**TRAX LRS**
- Laravel/Vue stack
- Supports MySQL, PostgreSQL, MongoDB, Elasticsearch
- [traxlrs.com](https://traxlrs.com/)

**Jupiter**
- Supports both xAPI and Caliper specifications
- [GitHub](https://github.com/Transcordia/jupiter)

---

## Commercial Solutions

### Rustici Software

Industry leaders who created xAPI (Tin Can API).

**Products:**
- **SCORM Cloud** - hosted service supporting SCORM 1.2/2004, AICC, xAPI, cmi5, LTI
- **Rustici Engine** - embeddable runtime for adding standards support to any LMS

**API features:**
- Unified API across all standards
- Webhooks for events
- Client libraries (Python, JavaScript, Ruby, .NET)

**Sources:**
- [Rustici Software](https://rusticisoftware.com/)
- [SCORM Cloud API](https://rusticisoftware.com/products/scorm-cloud/api/)

---

## WebAssembly Sandboxing

Emerging approach for safe execution of untrusted code, relevant to running user-provided backend logic.

**Security model:**
- Sandboxed memory - code cannot access host system
- Deny-by-default capabilities - must explicitly grant access
- WASI (WebAssembly System Interface) for controlled I/O

**Key properties:**
- Memory isolation via Software Fault Isolation (SFI)
- Capability-based security (opposite of containers)
- Cross-language support (compile from Rust, Go, Python, etc.)

**Research:**
- [WebAssembly Security Model](https://webassembly.org/docs/security/)
- [Wasmtime Security](https://docs.wasmtime.dev/security.html)
- [USENIX: Provably-Safe Sandboxing](https://www.usenix.org/conference/usenixsecurity22/presentation/bosamiya)
- [NVIDIA: Sandboxing AI Workflows](https://developer.nvidia.com/blog/sandboxing-agentic-ai-workflows-with-webassembly/)

---

## Gap Analysis

None of the existing standards support **backend code execution**:

| Standard | Frontend | Backend |
|----------|----------|---------|
| SCORM | Browser JS | None |
| xAPI | Browser JS | None (LRS is fixed infrastructure) |
| cmi5 | Browser JS | None |
| LTI | External tool UI | External (unpackaged, unsandboxed) |
| Common Cartridge | Static content | None |
| QTI | Declarative XML | None |
| H5P | Browser JS | None |
| XBlocks | Browser JS | Python (unsandboxed, tied to edX) |

**The gap:** Activities requiring server-side logic (AI tutoring, adaptive algorithms, secure grading, simulations) must be built as separate services and integrated via LTI. There's no standard way to:

1. Package backend code with learning content
2. Run it in a sandboxed environment
3. Control capabilities (API access, storage, LMS integration)
4. Deploy across different LMS platforms

---

## Comparison with Learning Activity Web Component

| Aspect | Traditional Standards | This Project |
|--------|----------------------|--------------|
| **Packaging** | ZIP + XML manifest | ES modules + JSON manifest |
| **Frontend** | SCORM JS API or static HTML | Web components with slots |
| **Backend** | None or external LTI service | Wasm plugins (Extism) |
| **Sandboxing** | None / iframe | Wasm memory isolation |
| **Capabilities** | All-or-nothing | Explicit manifest (kv, http, lms, ai) |
| **Extensibility** | QTI PCI (complex) | Just write JavaScript/any Wasm language |

**Novel contributions:**
1. Web Components for declarative, slot-based content
2. ES Modules for frontend interactivity (modern, no special tooling)
3. Wasm sandboxing for safe backend execution
4. Capability manifest inspired by Zed's model
5. Portable across LMS via thin native plugins
