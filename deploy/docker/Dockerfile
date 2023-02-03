# build stage
FROM python:3.11-slim AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /app/
COPY src/ /app/src

# install dependencies and project into the local packages directory
WORKDIR /app
RUN mkdir __pypackages__ && pdm install --prod --no-lock --no-editable


# run stage
FROM python:3.11-slim
RUN mkdir /app

# retrieve packages from build stage
ENV PYTHONPATH=/app/pkgs
COPY --from=builder /app/__pypackages__/3.11/lib /app/pkgs

ENV WORKERS=9
ENV API_KEY=API_KEY
EXPOSE 9900
CMD python -c "from uvicorn.main import main; main()" prometheus_mirror.mirror:app --workers $WORKERS --host 0.0.0.0 --port 9900

