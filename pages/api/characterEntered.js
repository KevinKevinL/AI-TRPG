// pages/api/characterEntered.js

export default async function handler(req, res) {
    if (req.method !== "POST") {
        return res.status(405).json({ error: "Only POST requests are allowed" });
    }

    const { character_id } = req.body;
    if (!character_id) {
        return res.status(400).json({ error: "Character ID is required." });
    }

    try {
        // 向 Python 后端发送请求
        const pythonBackendUrl = "http://localhost:8000/api/character_entered";

        const backendResponse = await fetch(pythonBackendUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ character_id }),
        });
        
        // 确保响应成功
        if (!backendResponse.ok) {
            const errorData = await backendResponse.json();
            throw new Error(errorData.detail || "Python backend returned an error.");
        }
        
        const data = await backendResponse.json();
        return res.status(200).json(data);

    } catch (err) {
        console.error("Error in /api/characterEntered:", err.message);
        return res.status(500).json({ error: "Failed to send character ID to backend. Check the Python backend." });
    }
}
