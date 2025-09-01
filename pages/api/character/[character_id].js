// pages/api/character/[character_id].js
export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Only GET requests are allowed" });
  }

  const { character_id } = req.query;
  
  if (!character_id) {
    return res.status(400).json({ error: "Character ID is required" });
  }

  try {
    const pythonBackendUrl = `http://localhost:8000/api/character_sheet/${character_id}`;

    const backendResponse = await fetch(pythonBackendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();
      throw new Error(errorData.detail || "Python backend returned an error.");
    }

    const data = await backendResponse.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error("Error in /api/character/[character_id]:", error.message);
    return res.status(500).json({ error: "Failed to communicate with Python backend." });
  }
}
