# MergeMind JavaScript Sandbox
# Minimal, locked-down execution container for JavaScript/Node verification
FROM node:20-slim

ENV CI=true \
    DEBIAN_FRONTEND=noninteractive

# Create unprivileged non-root user (node user is pre-built in official node image)
WORKDIR /workspace
RUN chown -R node:node /workspace

USER node

CMD ["npm", "test"]
