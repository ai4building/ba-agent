# BA-Agent Python Service - hxPy Compatible Docker Image
# This image extends the official Haxall hxPy image with BA-Agent AI dependencies.
#
# Build: docker build -t ba-agent-py:latest -f src/baAgentPy/Dockerfile .
# Usage in Haxall: py(image: "ba-agent-py:latest")
#
# Project: https://github.com/your-org/ba-agent
# Registry: ghcr.io/your-org/ba-agent-py

ARG PYTHON_VERSION=3.13

FROM --platform=linux/amd64 ghcr.io/haxall/hxpy:latest

# Metadata
LABEL maintainer="BA-Agent Team"
LABEL description="BA-Agent AI Service for FIN Framework/Haxall with LLM intent parsing"
LABEL version="0.1.0"

# Set working directory
WORKDIR /usr/src

# Copy project files
# baAgentPy structure:
#   __init__.py
#   main.py              <- BaAgentService entry point
#   core/
#     agent_workflow.py   <- Task routing
#   services/
#     base.py            <- BaseEngine interface
#     fdd_engine.py        <- Fault Detection & Diagnosis
#     energy_opt.py        <- Energy Optimization
#     inspect_engine.py      <- Virtual Inspection
#     hmi_engine.py         <- HMI Generation
#     report_engine.py       <- Report Generation
#     tagging_engine.py      <- Auto-tagging
#   utils/
#     grid_converter.py    <- Haystack Grid conversion

COPY src/baAgentPy/ /io/baAgentPy/

# Install additional Python dependencies using pip
# These are the AI/ML libraries not included in base hxPy image
RUN --mount=type=cache,target=/root/.cache \
    pip install --no-cache-dir \
    langchain>=0.3.0 \
    langchain-core>=0.3.0 \
    google-generativeai>=0.8.0 \
    requests>=2.32.0 \
    pydantic>=2.0.0

# Environment variables (must be set before verification)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/io:/io/baAgentPy

# Verify installation (now PYTHONPATH is set)
RUN python -c "import baAgentPy; print('BA-Agent loaded successfully')"

# The /io/ directory is mounted by Haxall for runtime data exchange
VOLUME ["/io"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from baAgentPy.main import BaAgentService; BaAgentService().handle('ping', {})"

# Default command (hxPy will override this when loading the module)
# The actual entry point is BaAgentService class instantiated by Haxall's pyEval()
CMD ["python", "-m", "baAgentPy.main"]
