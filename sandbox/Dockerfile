# Throwaway sandbox for Ahmes's brain. No network, no secrets, read-only, non-root (set at run time).
FROM python:3.12-slim
# The base image sets GPG_KEY (its public signing-key ID). Blank it so nothing key-like is visible.
ENV GPG_KEY=
COPY runner.py /runner.py
RUN chmod 0444 /runner.py
USER 65534:65534
ENTRYPOINT ["timeout", "-s", "KILL", "3", "python", "-I", "-S", "-B", "/runner.py"]
