from flask import Flask, render_template, request, send_from_directory, send_file
import os
import random
import requests
import io
import itertools
from urllib.parse import urlparse

app = Flask(__name__)

UNSPLASH_ACCESS_KEY = "2VKRGt47R34jrj8OBe7iuOUdfFQeAXsD8G1nazxCoqg"

# Define all wallpaper categories (you can add/remove easily here)
CATEGORIES = [
    "pc", "mobile", "anime", "cyberpunk", "linux", "misc", "nature", "nord", "themes", "purple", "space", "windows"
]

# Load wallpapers into a dictionary {category: [images]}
wallpapers_dict = {}
for category in CATEGORIES:
    category_dir = os.path.join(app.static_folder, "wallpapers", category)
    wallpapers_dict[category] = (
        os.listdir(category_dir) if os.path.exists(category_dir) else []
    )

# Flatten dict into (category, image) pairs
get_all_wallpapers = lambda d: list(
    itertools.chain.from_iterable(
        [(cat, img) for img in imgs] for cat, imgs in d.items()
    )
)

@app.route('/')
def index():
    all_wallpapers = get_all_wallpapers(wallpapers_dict)

    # Show up to 100 random wallpapers on homepage
    num_random_wallpapers = min(100, len(all_wallpapers)) if all_wallpapers else 0
    random_wallpapers = (
        random.sample(all_wallpapers, num_random_wallpapers) if num_random_wallpapers > 0 else []
    )

    return render_template('index.html', random_wallpapers=random_wallpapers)

# Dynamic route for each category
@app.route('/<category>')
def show_wallpapers(category):
    if category not in wallpapers_dict:
        return "Category not found", 404
    wallpapers = wallpapers_dict[category][:]
    random.shuffle(wallpapers)
    return render_template('category.html', category=category, wallpapers=wallpapers)

# Special "all wallpapers" route
@app.route('/all')
def show_all_wallpapers():
    all_wallpapers = get_all_wallpapers(wallpapers_dict)
    random.shuffle(all_wallpapers)
    return render_template("all.html", wallpapers=all_wallpapers)

@app.route('/search')
def search():
    query = request.args.get('query')
    page = request.args.get('page', 1, type=int)

    if not query:
        return render_template('search.html', query=None, images=None)

    url = "https://api.unsplash.com/search/photos"
    params = {
        'query': query,
        'per_page': 30,
        'page': page,
        'client_id': UNSPLASH_ACCESS_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        images = data.get('results', [])

        total_results = data.get('total', 0)
        total_pages = (total_results + 29) // 30

        return render_template(
            'search.html',
            query=query,
            images=images,
            page=page,
            total_pages=total_pages
        )
    except requests.exceptions.RequestException as e:
        print(f"Error fetching images from Unsplash: {e}")
        return render_template('search.html', query=query, images=None, error="Failed to fetch images from Unsplash. Please try again later.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        return render_template('search.html', query=query, images=None, error="An unexpected error occurred.")

@app.route('/download/unsplash/<image_id>')
def download_unsplash(image_id):
    download_url = f"https://api.unsplash.com/photos/{image_id}/download"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}

    try:
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()
        download_location = response.json().get('url')

        if not download_location:
            return "Error: Download location not found.", 500

        image_response = requests.get(download_location, stream=True)
        image_response.raise_for_status()

        parsed_url = urlparse(download_location)
        filename = os.path.basename(parsed_url.path) or f"wallpaper_{image_id}.jpg"

        if not os.path.splitext(filename)[1]:
            filename += ".jpg"

        image_buffer = io.BytesIO(image_response.content)

        return send_file(
            image_buffer,
            mimetype=image_response.headers.get('Content-Type', 'image/jpeg'),
            as_attachment=True,
            download_name=filename
        )

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return f"Error downloading image: {e}", 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Unexpected error occurred: {e}", 500

@app.route('/download/<device>/<filename>')
def download_local(device, filename):
    wallpapers_dir = os.path.join(app.static_folder, 'wallpapers', device)
    if not os.path.exists(wallpapers_dir):
        return "Directory not found.", 404
    return send_from_directory(wallpapers_dir, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
