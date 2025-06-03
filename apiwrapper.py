from flask import Flask, request, jsonify
import asyncio
import json
from browser_use import Agent
import os
from threading import Thread
import time

app = Flask(__name__)

# Simple in-memory storage for async results
results_store = {}

def run_browser_task(task_id, prompt, model_name="gpt-4o-mini"):
    """Run browser automation task and store result"""
    try:
        async def browser_automation():
            agent = Agent(
                task=prompt,
                llm=model_name,
                use_vision=True,
                save_conversation_path=f"./conversations/{task_id}.json"
            )
            result = await agent.run()
            return result
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(browser_automation())
        
        results_store[task_id] = {
            "status": "completed",
            "result": str(result),
            "timestamp": time.time()
        }
        
    except Exception as e:
        results_store[task_id] = {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "service": "browser-use-api"})

@app.route('/browser/run', methods=['POST'])
def run_browser_automation():
    """
    Run browser automation task
    Expected JSON payload:
    {
        "prompt": "Your automation task description",
        "model": "gpt-4o-mini" (optional),
        "async": true/false (optional, default: false)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({"error": "Missing 'prompt' in request body"}), 400
        
        prompt = data['prompt']
        model_name = data.get('model', 'gpt-4o-mini')
        is_async = data.get('async', False)
        
        if is_async:
            # Generate task ID for async processing
            task_id = f"task_{int(time.time() * 1000)}"
            
            # Start browser task in background thread
            thread = Thread(target=run_browser_task, args=(task_id, prompt, model_name))
            thread.start()
            
            return jsonify({
                "task_id": task_id,
                "status": "started",
                "message": "Task started. Use /browser/status/{task_id} to check progress"
            })
        else:
            # Synchronous execution
            async def run_sync():
                agent = Agent(
                    task=prompt,
                    llm=model_name,
                    use_vision=True
                )
                result = await agent.run()
                return result
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_sync())
            
            return jsonify({
                "status": "completed",
                "result": str(result),
                "prompt": prompt
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/browser/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of async browser automation task"""
    if task_id not in results_store:
        return jsonify({"error": "Task not found"}), 404
    
    return jsonify(results_store[task_id])

@app.route('/browser/simple', methods=['POST'])
def simple_browser_task():
    """
    Simplified endpoint for common browser tasks
    Expected JSON payload:
    {
        "action": "search" | "scrape" | "click" | "fill_form",
        "target": "URL or search term",
        "data": {} (additional data for the action)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'action' not in data or 'target' not in data:
            return jsonify({"error": "Missing 'action' or 'target' in request body"}), 400
        
        action = data['action']
        target = data['target']
        extra_data = data.get('data', {})
        
        # Create prompt based on action
        prompts = {
            "search": f"Search for '{target}' on Google and return the top 3 results with titles and URLs",
            "scrape": f"Go to {target} and extract the main content, headings, and key information from the page",
            "click": f"Go to {target} and click on the element: {extra_data.get('element', 'submit button')}",
            "fill_form": f"Go to {target} and fill out the form with this data: {json.dumps(extra_data)}"
        }
        
        if action not in prompts:
            return jsonify({"error": f"Unsupported action: {action}"}), 400
        
        prompt = prompts[action]
        
        # Run the browser automation
        async def run_simple_task():
            agent = Agent(
                task=prompt,
                llm="gpt-4o-mini",
                use_vision=True
            )
            result = await agent.run()
            return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_simple_task())
        
        return jsonify({
            "status": "completed",
            "action": action,
            "target": target,
            "result": str(result)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create conversations directory
    os.makedirs('./conversations', exist_ok=True)
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
