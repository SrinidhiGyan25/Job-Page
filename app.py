from flask import Flask, render_template_string, jsonify
import os
import threading
import time
import schedule
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import random
import json

app = Flask(__name__)

# Global variables to store scraped data
job_data = []
last_updated = None
scraping_in_progress = False

def setup_chrome_driver():
    """Setup Chrome driver with webdriver-manager for automatic version matching"""
    options = Options()
    
    # Essential headless options for server deployment
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-images')
    options.add_argument('--disable-javascript')
    
    # Window and memory settings
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--memory-pressure-off')
    options.add_argument('--single-process')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    
    # Anti-detection measures
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Additional stability options
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-logging')
    options.add_argument('--disable-permissions-api')
    options.add_argument('--disable-popup-blocking')
    
    try:
        # Use webdriver-manager to automatically download and setup ChromeDriver
        options.binary_location = "/usr/bin/chromium"  # Use system Chromium
        service = Service("/usr/bin/chromedriver")     # Use system ChromeDriver

        driver = webdriver.Chrome(service=service, options=options)
        
        # Additional anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ Chrome driver setup successful")
        return driver
    except Exception as e:
        print(f"❌ Chrome setup failed: {e}")
        return None

def scrape_naukri_jobs(query="Data Scientist", pages=2):
    """Scrape Naukri jobs"""
    global job_data, last_updated, scraping_in_progress
    
    scraping_in_progress = True
    print(f"🚀 Starting scrape for '{query}' at {datetime.now()}")
    
    driver = setup_chrome_driver()
    if not driver:
        print("❌ Failed to setup Chrome driver")
        scraping_in_progress = False
        return []
    
    wait = WebDriverWait(driver, 20)
    scraped_jobs = []
    
    try:
        for page in range(1, pages + 1):
            url = f"https://www.naukri.com/{query.replace(' ', '-')}-jobs-{page}?k={query}"
            print(f"🔍 Scraping page {page}")
            
            try:
                driver.get(url)
                time.sleep(random.randint(3, 6))
                
                # Check if blocked
                if "blocked" in driver.page_source.lower() or "captcha" in driver.page_source.lower():
                    print("❌ Blocked or captcha detected")
                    break
                
                # Wait for job cards
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "srp-jobtuple-wrapper")]')))
                except:
                    print(f"⚠️ No job cards found on page {page}")
                    continue
                
                job_cards = driver.find_elements(By.XPATH, '//div[contains(@class, "srp-jobtuple-wrapper")]')
                print(f"📋 Found {len(job_cards)} job cards")
                
                for card in job_cards:
                    try:
                        # Extract job data
                        title = card.find_element(By.XPATH, './/a[contains(@class, "title")]').text.strip()
                        
                        try:
                            location = card.find_element(By.XPATH, './/span[contains(@class, "locWdth")]').text.strip()
                        except:
                            location = "N/A"
                        
                        try:
                            experience = card.find_element(By.XPATH, './/span[contains(@class, "expwdth")]').text.strip()
                        except:
                            experience = "N/A"
                        
                        try:
                            description = card.find_element(By.XPATH, './/span[contains(@class, "job-desc")]').text.strip()
                        except:
                            description = "N/A"
                        
                        try:
                            company = card.find_element(By.XPATH, './/a[contains(@class, "subTitle")]').text.strip()
                        except:
                            company = "N/A"
                        
                        try:
                            salary = card.find_element(By.XPATH, './/span[contains(@class, "sal")]').text.strip()
                        except:
                            salary = "N/A"
                        
                        try:
                            title_element = card.find_element(By.XPATH, './/a[contains(@class, "title")]')
                            job_url = title_element.get_attribute('href')
                        except:
                            job_url = "N/A"
                        
                        if title and title != "N/A":
                            scraped_jobs.append({
                                "title": title,
                                "company": company,
                                "location": location,
                                "experience": experience,
                                "salary": salary,
                                "description": description[:200] + "..." if len(description) > 200 else description,
                                "url": job_url,
                                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        
                    except Exception as e:
                        print(f"⚠️ Error extracting job: {e}")
                        continue
                
                # Delay between pages
                if page < pages:
                    time.sleep(random.randint(5, 10))
                    
            except Exception as e:
                print(f"❌ Error on page {page}: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        driver.quit()
    
    # Update global data
    job_data = scraped_jobs
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scraping_in_progress = False
    
    print(f"✅ Scraping completed! Total jobs: {len(scraped_jobs)}")
    return scraped_jobs

def schedule_scraping():
    """Schedule the scraping task"""
    def run_scraper():
        scrape_naukri_jobs("Data Scientist", pages=2)
    
    # Schedule scraping every hour
    schedule.every().hour.do(run_scraper)
    
    # Run initial scrape
    run_scraper()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# HTML template for the job listings page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Latest Data Science Jobs - Naukri</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .stat-item {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 25px;
            backdrop-filter: blur(10px);
        }
        
        .content {
            padding: 30px;
        }
        
        .job-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }
        
        .job-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.15);
        }
        
        .job-title {
            font-size: 1.4rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .job-company {
            font-size: 1.1rem;
            color: #e74c3c;
            font-weight: 600;
            margin-bottom: 15px;
        }
        
        .job-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .detail-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .detail-icon {
            width: 20px;
            height: 20px;
            background: #667eea;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
        }
        
        .job-description {
            color: #555;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        
        .apply-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 25px;
            text-decoration: none;
            display: inline-block;
            font-weight: 600;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .apply-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: #666;
        }
        
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 10px 20px rgba(231, 76, 60, 0.3);
            transition: all 0.3s ease;
        }
        
        .refresh-btn:hover {
            transform: scale(1.1);
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .stats {
                gap: 15px;
            }
            
            .content {
                padding: 20px;
            }
            
            .job-details {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Latest Data Science Jobs</h1>
            <p>Fresh opportunities updated every hour from Naukri.com</p>
            <div class="stats">
                <div class="stat-item">
                    <strong>{{ total_jobs }}</strong> Jobs Available
                </div>
                <div class="stat-item">
                    Last Updated: <strong>{{ last_updated or 'Never' }}</strong>
                </div>
                {% if scraping_in_progress %}
                <div class="stat-item">
                    🔄 Updating...
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="content">
            {% if not jobs %}
                <div class="loading">
                    <h2>🔄 Loading latest jobs...</h2>
                    <p>Please wait while we fetch the latest opportunities for you!</p>
                </div>
            {% else %}
                {% for job in jobs %}
                <div class="job-card">
                    <div class="job-title">{{ job.title }}</div>
                    <div class="job-company">🏢 {{ job.company }}</div>
                    
                    <div class="job-details">
                        <div class="detail-item">
                            <div class="detail-icon">📍</div>
                            <span>{{ job.location }}</span>
                        </div>
                        <div class="detail-item">
                            <div class="detail-icon">💼</div>
                            <span>{{ job.experience }}</span>
                        </div>
                        {% if job.salary != 'N/A' %}
                        <div class="detail-item">
                            <div class="detail-icon">💰</div>
                            <span>{{ job.salary }}</span>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if job.description != 'N/A' %}
                    <div class="job-description">{{ job.description }}</div>
                    {% endif %}
                    
                    {% if job.url != 'N/A' %}
                    <a href="{{ job.url }}" target="_blank" class="apply-btn">Apply Now →</a>
                    {% endif %}
                </div>
                {% endfor %}
            {% endif %}
        </div>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()" title="Refresh">🔄</button>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => {
            location.reload();
        }, 300000);
        
        // Add some interactivity
        document.querySelectorAll('.job-card').forEach(card => {
            card.addEventListener('click', function() {
                this.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 100);
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Main route to display jobs"""
    return render_template_string(
        HTML_TEMPLATE,
        jobs=job_data,
        total_jobs=len(job_data),
        last_updated=last_updated,
        scraping_in_progress=scraping_in_progress
    )

@app.route('/api/jobs')
def api_jobs():
    """API endpoint to get jobs as JSON"""
    return jsonify({
        'jobs': job_data,
        'total_jobs': len(job_data),
        'last_updated': last_updated,
        'scraping_in_progress': scraping_in_progress
    })

@app.route('/refresh')
def manual_refresh():
    """Manual refresh endpoint"""
    if not scraping_in_progress:
        thread = threading.Thread(target=lambda: scrape_naukri_jobs("Data Scientist", pages=2))
        thread.daemon = True
        thread.start()
    return jsonify({'status': 'refresh_started'})

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'jobs_count': len(job_data),
        'last_updated': last_updated
    })

if __name__ == '__main__':
    # Start the background scraping scheduler
    scheduler_thread = threading.Thread(target=schedule_scraping)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)