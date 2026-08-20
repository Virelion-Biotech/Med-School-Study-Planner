FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY planner ./planner
COPY tests ./tests
RUN pip install --no-cache-dir -e '.[all]'
ENV STUDY_PLANNER_DB=/data/study_planner.db
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn","planner.api:app","--host","0.0.0.0","--port","8000"]
