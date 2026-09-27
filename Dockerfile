FROM apify/actor-python:3.12

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . ./

# Run Actor
CMD ["python3", "-m", "src.main"]
