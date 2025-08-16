/*
import { generateCharacterDescription } from "../../ai/generateCharacterDescription.js";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Only POST requests are allowed" });
  }
  
  const { prompt } = req.body;
  if (!prompt) {
    return res.status(400).json({ error: "Prompt is required." });
  }
  
  try {
    const descriptionData = await generateCharacterDescription(prompt);
    return res.status(200).json({ description: descriptionData.description });
  } catch (err) {
    console.error("Error in /api/characterDescription:", err);
    return res.status(500).json({ error: "Failed to generate character description." });
  }
}
*/

// pages/api/characterDescription.js

export default async function handler(req, res) {
    if (req.method !== "POST") {
        return res.status(405).json({ error: "Only POST requests are allowed" });
    }

    const { prompt } = req.body;
    if (!prompt) {
        return res.status(400).json({ error: "Prompt is required." });
    }

    try {
        // 向 Python 后端发送请求
        const pythonBackendUrl = "http://localhost:8000/api/generate_description";

        const backendResponse = await fetch(pythonBackendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt }),
        });
        
        // 确保响应成功
        if (!backendResponse.ok) {
            const errorData = await backendResponse.json();
            throw new Error(errorData.detail || "Python backend returned an error.");
        }
        
        const data = await backendResponse.json();
        return res.status(200).json(data);

    } catch (err) {
        console.error("Error in /api/characterDescription:", err.message);
        return res.status(500).json({ error: "Failed to generate character description. Check the Python backend." });
    }
}
