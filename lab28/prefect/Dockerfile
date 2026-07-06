FROM prefecthq/prefect:2.14.0-python3.10

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /opt/prefect/flows
