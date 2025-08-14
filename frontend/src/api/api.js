// TODO: Add request timeout handling
// FIXME: Sometimes the streaming gets stuck, need to investigate

export const getAIMessage = async (userQuery, conversationId = null, onProgressUpdate = null) => {
  // console.log('Making API call with query:', userQuery); // debug
  try {
    // Call our new FastAPI backend with streaming
    const response = await fetch('http://localhost:8000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 'Authorization': 'Bearer ' + token, // TODO: Add auth later
      },
      body: JSON.stringify({
        query: userQuery,
        conversation_id: conversationId,  // Pass conversation ID for context
        stream: true,  // Enable progressive streaming
        // max_tokens: 2000, // might add this later
      })
    });

    if (!response.ok) {
      //Better error handling based on status codes
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    // Handle streaming response - this was tricky to get right
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8'); // explicit encoding
    
    let aiResponse = '';
    let partsData = []; // renamed for clarity
    let repairsData = [];
    let blogsData = [];
    let responseTime = null;
    let returnedConversationId = conversationId; // Track the conversation ID returned by backend
    // let chunkCount = 0; // for debugging streaming issues
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // chunkCount++; // debug counter
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        // console.log('Processing chunk:', lines.length, 'lines'); // debug
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              
              // Track conversation ID from backend
              if (data.conversation_id) {
                returnedConversationId = data.conversation_id;
                console.log('📌 Backend conversation ID:', returnedConversationId);
              }
              
              // Handle different types of streaming data
              // NOTE: Added more cases as backend evolved
              switch (data.type) {
                case 'thinking':
                  if (onProgressUpdate) onProgressUpdate({ type: 'thinking', content: data.content });
                  break;
                  
                case 'response':
                  aiResponse = data.content;
                  if (onProgressUpdate) onProgressUpdate({ type: 'response', content: data.content });
                  break;
                  
                case 'parts':
                  partsData = data.content;
                  if (onProgressUpdate) onProgressUpdate({ type: 'parts', content: data.content });
                  break;
                  
                case 'repairs':
                  repairsData = data.content;
                  if (onProgressUpdate) onProgressUpdate({ type: 'repairs', content: data.content });
                  break;
                  
                case 'blogs':
                  blogsData = data.content;
                  if (onProgressUpdate) onProgressUpdate({ type: 'blogs', content: data.content });
                  break;
                  
                case 'complete':
                  responseTime = data.response_time ? data.response_time.toFixed(1) : null;
                  // console.log('Request completed in', responseTime, 'seconds'); // debug
                  if (onProgressUpdate) onProgressUpdate({ type: 'complete', responseTime });
                  break;
                  
                case 'error':
                  throw new Error(data.content);
              }
            } catch (parseError) {
              // This happens sometimes with incomplete JSON chunks - annoying but whatever
              console.warn('Failed to parse streaming data:', parseError, 'Raw line:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    // Build final response (fallback to non-streaming format)
    // This structure matches what the old API used to return
    const data = { response: aiResponse, parts: partsData, repairs: repairsData, blogs: blogsData, response_time: responseTime };
    
    // Format response for the chat interface
    // TODO: Move this formatting logic to a separate function
    let content = data.response;
    
    // Update response time if not already set from streaming
    if (!responseTime && data.response_time) {
      responseTime = data.response_time.toFixed(1); // keep as seconds with 1 decimal
    }
    
    // If we have parts, add them to the response with better formatting
    // NOTE: This formatting took several iterations to get right
    if (data.parts && data.parts.length > 0) {
      content += "\n\n---\n\n";
      data.parts.forEach((part, idx) => { // shortened variable name
        content += `### ${idx + 1}. ${part.name}\n`;
        content += `**Part #:** ${part.part_number} | **Price:** $${part.price} | **Brand:** ${part.brand}\n`;
        
        if (part.manufacturer_number) {
          content += `**Manufacturer #:** ${part.manufacturer_number}\n`;
        }
        
        if (part.appliance_types) {
          content += `**For:** ${part.appliance_types}\n`;
        }
        
        content += `**Availability:** ${part.stock_status}\n\n`;
        
        if (part.install_difficulty && part.install_time) {
          content += `**Installation:** ${part.install_difficulty} difficulty (${part.install_time})\n\n`;
        }
        
        if (part.symptoms) {
          content += `**Fixes these symptoms:** ${part.symptoms}\n\n`;
        }
        
        if (part.replace_parts) {
          content += `**Replaces parts:** ${part.replace_parts}\n\n`;
        }
        
        if (part.url) {
          content += `[📋 View Part Details](${part.url})\n`;
          
          // Add a part image if available (try common PartSelect pattern)
          if (part.part_number && part.part_number.trim()) {
            const partImageUrl = `https://www.partselect.com/images/parts/${part.part_number}_1.jpg`;
            content += `![${part.name}](${partImageUrl} "Part Image - ${part.name}")\n`;
          }
        }
        
        if (part.install_video_url) {
          content += `[📹 Installation Video](${part.install_video_url})\n`;
        }
        
        if (idx < data.parts.length - 1) {
          content += "\n---\n\n";
        }
      });
    }

    // If we have repairs, add them to the response
    if (data.repairs && data.repairs.length > 0) {
      content += "\n\n## Repair Guides\n\n";
      data.repairs.forEach((repair, i) => { // different variable name for variety
        content += `### ${i + 1}. ${repair.title}\n`;
        
        if (repair.appliance_type) {
          content += `**For:** ${repair.appliance_type}\n`;
        }
        
        if (repair.difficulty) {
          content += `**Difficulty:** ${repair.difficulty}\n`;
        }
        
        if (repair.estimated_time) {
          content += `**Time:** ${repair.estimated_time}\n`;
        }
        
        if (repair.parts_needed && repair.parts_needed.length > 0) {
          content += `**Parts Needed:** ${repair.parts_needed.join(', ')}\n`;
        }
        
        if (repair.url) {
          content += `[🔧 View Repair Guide](${repair.url})\n`;
        }
        
        if (i < data.repairs.length - 1) {
          content += "\n";
        }
      });
    }

    // Clean, simple blog links - kept this simple on purpose
    if (data.blogs && data.blogs.length > 0) {
      content += "\n\n**Articles that may be helpful:**\n";
      data.blogs.forEach((blogPost) => { // more descriptive name
        if (blogPost.title && blogPost.url) {
          content += `- [${blogPost.title}](${blogPost.url})\n`;
        }
      });
    }

    return {
      response: aiResponse,
      parts: partsData,
      repairs: repairsData, 
      blogs: blogsData,
      responseTime: responseTime,
      conversationId: returnedConversationId // Return the backend conversation ID
    };

  } catch (error) {
    console.error('Error calling chat API:', error);
    // TODO: Add different error messages based on error type
    // FIXME: This generic error message kinda sucks
    return {
      role: "assistant", 
      content: "Sorry, I'm having trouble connecting to the server. Please make sure the backend is running on http://localhost:8000"
    };
  }
};

// Helper function for debugging - not used in production
// const logApiResponse = (response) => {
//   console.log('API Response:', response);
// };
