FROM naturebench-eval:main

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/naturebench

COPY naturebench_eval_service /opt/naturebench/naturebench_eval_service
COPY bin /opt/naturebench/bin
COPY evaluation /evaluation
COPY metadata.json /metadata.json

RUN chmod +x /opt/naturebench/bin/timerctl /opt/naturebench/bin/drain-and-finalize \
    && mkdir -p /state /run/naturebench

EXPOSE 8000
ENTRYPOINT ["python", "-m", "naturebench_eval_service.server"]
