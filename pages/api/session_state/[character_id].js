// pages/api/session_state/[character_id].js
export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const { character_id } = req.query;

  if (!character_id) {
    return res.status(400).json({ message: 'Character ID is required' });
  }

  try {
    // 转发请求到后端
    const response = await fetch(`http://localhost:8000/api/session_state/${character_id}`);
    
    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    console.error('Error fetching session state:', error);
    res.status(500).json({ message: 'Failed to fetch session state', error: error.message });
  }
}
