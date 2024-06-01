import gzip
import logging
import nltk
import os
from rake_nltk import Rake
from bs4 import BeautifulSoup
import urllib.request
from googlesearch import search
import random
import chardet
import re
import azure.functions as func
import PyPDF2
import io

# Set NLTK data directory to a temporary directory
nltk_data_dir = '/tmp/nltk_data'
os.makedirs(nltk_data_dir, exist_ok=True)
nltk.data.path.append(nltk_data_dir)

# Download NLTK stopwords corpus and punkt tokenizer if not already downloaded
nltk.download('stopwords', download_dir=nltk_data_dir)
nltk.download('punkt', download_dir=nltk_data_dir)

def search_images(keywords, num_images=4):
    images = []
    for keyword in keywords:
        url = f"https://source.unsplash.com/featured/?{keyword}"
        for _ in range(num_images):
            images.append(url)
    return images

def fetch_content(url, encoding='utf-8'):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://www.google.com',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    req = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(req)
    content_encoding = response.info().get('Content-Encoding')
    
    if 'application/pdf' in response.info().get('Content-Type'):
        pdf_data = response.read()
        return extract_text_from_pdf(pdf_data)
    
    html = response.read()
    
    if content_encoding == 'gzip':
        html = gzip.decompress(html)
    elif content_encoding == 'deflate':
        html = zlib.decompress(html)

    detected_encoding = chardet.detect(html)['encoding']
    try:
        return html.decode(detected_encoding or encoding)
    except UnicodeDecodeError:
        try:
            return html.decode('latin-1')  # Fallback to latin-1
        except UnicodeDecodeError:
            return html.decode('utf-8', errors='ignore') # Ignore errors and decode

def extract_text_from_pdf(pdf_data):
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="agen")
def agen(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')


    user_input = req.params.get('question')
    if not user_input:
        try:
            req_body = req.get_json()
        except ValueError:
            req_body = None 
        else:
            user_input = req_body.get('question')
        if not user_input:
            return func.HttpResponse(
                "Please pass an assignment question on the query string or in the request body",
                status_code=400
            )
    template = req.params.get('template')

    r = Rake()
    r.extract_keywords_from_text(user_input)
    keywords = r.get_ranked_phrases()

    related_urls = []
    try:
        for keyword in keywords:
            for url in search(keyword, num_results=5):
                related_urls.append(url)
    except Exception as e:
        logging.error(f"Error fetching search results: {e}")

    relevant_content = ""
    for url in related_urls:
        try:
            content = fetch_content(url)
            if url.endswith('.pdf'):
                relevant_content += content + '\n\n'
            else:
                soup = BeautifulSoup(content, 'html.parser')
                paragraphs = [tag.get_text().strip() for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])]
                relevant_paragraphs = []
                for paragraph in paragraphs:
                    if any(keyword.lower() in paragraph.lower() for keyword in keywords):
                        relevant_paragraphs.append(paragraph)
                        if len(relevant_paragraphs) == 3:
                            break
                if relevant_paragraphs:
                    relevant_content += '\n\n'.join(relevant_paragraphs) + '\n\n'
        except Exception as e:
            logging.error(f"Error fetching content from {url}: {e}")

    references = []
    for url in related_urls:
        try:
            content = fetch_content(url, encoding='utf-8')
            if not url.endswith('.pdf'):
                soup = BeautifulSoup(content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    if 'http' in link['href']:
                        references.append(link['href'])
        except Exception as e:
            logging.error(f"Error fetching references from {url}: {e}")

    references = references[:10]

    images = search_images(keywords, num_images=4)
    unique_images = list(set(images))
    if len(unique_images) < 2:
        additional_images = search_images(keywords, num_images=2)
        unique_images.extend(additional_images)
    random.shuffle(unique_images)
    image_chunks = [unique_images[i:i+4] for i in range(0, len(unique_images), 4)]

    image_grid_html = ''
    for chunk in image_chunks:
        image_grid_html += '<div class="image-grid">'
        for image in chunk:
            image_grid_html += f'<img src="{image}" alt="Image">'
        image_grid_html += '</div>'

    relevant_content = relevant_content.encode('utf-8', 'ignore').decode('utf-8')
    references = [re.sub(r'[^\x00-\x7F]+', '', ref) for ref in references]
    references = [ref.encode('utf-8', 'ignore').decode('utf-8') for ref in references]
    keywords = [re.sub(r'[^\x00-\x7F]+', '', kw) for kw in keywords]
    keywords = [kw.encode('utf-8', 'ignore').decode('utf-8') for kw in keywords]

    
    images = f"<h2>Images:</h2>\n{image_grid_html}"
    if (template == "e"):
        images = ""
    elif (template == "m"):
        pass
    elif (template == "h"):
        pass
    elif (template == "b"):
        pass
    assignment_text = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                font-size: 12px;
                line-height: 1.8;
                padding: 20px;
                border: 2px solid #000;
                text-align: justify;
            }}
            h1 {{
                font-size: 20px;
                font-weight: bold;
                margin-top: 30px;
                margin-bottom: 20px;
            }}
            h2 {{
                font-size: 17px;
                font-weight: bold;
                margin-top: 25px;
                margin-bottom: 15px;
            }}
            h3 {{
                font-size: 15px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 10px;
            }}
            p {{
                margin-top: 12px;
                margin-bottom: 12px;
            }}
            .image-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                grid-gap: 20px;
            }}
            img {{
                max-width: 100%;
                height: auto;
            }}
        </style>
    </head>
    <body>
    <h1>Topic: {', '.join(keywords)}</h1>
    <h2>Relevant Content:</h2>
    {relevant_content}
    {images}
    <h2>References:</h2>
    <ul>
    {"".join(f'<li><a href="{reference}">{reference}</a></li>' for reference in references)}
    </ul>
    </body>
    </html>
    """
    assignment_text = assignment_text.encode('utf-8', 'ignore').decode('utf-8')

    return func.HttpResponse(assignment_text, mimetype="text/html")
