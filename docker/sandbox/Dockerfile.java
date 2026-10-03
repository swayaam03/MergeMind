# MergeMind Java Sandbox
# Minimal, locked-down execution container for Java compilation and tests
FROM openjdk:17-slim

ENV CI=true \
    DEBIAN_FRONTEND=noninteractive

# Create unprivileged non-root user
RUN groupadd -g 1000 sandbox && \
    useradd -u 1000 -g sandbox -m -s /bin/bash sandbox

WORKDIR /workspace
RUN chown -R sandbox:sandbox /workspace

USER sandbox

CMD ["javac"]
