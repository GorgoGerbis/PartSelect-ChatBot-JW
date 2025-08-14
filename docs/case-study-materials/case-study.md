# Instalily AI Case Study - PartSelect Chat Agent

## Timeline
**Deadline:** Tuesday, August 12, 2025 at 5:36 PM EDT  
**Duration:** 2 days from start

## Submission Requirements
- **Source code** (complete implementation)
- **Loom video walkthrough** (demonstration and explanation)
- **Optional:** Slide deck or visual aids to explain design choices and implementation

*Note: Be creative with your submission format and presentation!*

## Project Overview

### Background
Design and develop a chat agent for the **PartSelect e-commerce website** with the following specifications:

- **Product Focus:** Refrigerator and Dishwasher parts only
- **Primary Function:** Provide product information and assist with customer transactions
- **Scope Constraint:** Agent must remain focused on this specific use case, avoiding responses to questions outside this scope
- **Key Priorities:** User experience and extensibility of implementation

### Frontend Requirements
- **Framework:** Modern framework (e.g., React)
- **Branding:** Must align with PartSelect's visual identity
- **Feature Selection:** Consider what users want from the chat agent:
  - Product information display
  - Visual product presentation in chat
  - Order support functionality
  - Installation guidance
  - Compatibility checking
  - Troubleshooting assistance

### Backend Requirements
- **Architecture:** Any backend architecture of your choice
- **Tools:** Free to use any online tools, vector databases, and supplementary materials
- **LLM Integration:** **Must include integration with DeepSeek language model**
- **Data Management:** Implement efficient product catalog search and retrieval

## Success Criteria

Your implementation will be evaluated on:

1. **Interface Design** - User experience and visual appeal
2. **Agentic Architecture** - How well the AI agent is structured and operates
3. **Extensibility** - How easily the system can be expanded or modified
4. **Scalability** - System's ability to handle growth and increased load
5. **Query Accuracy** - Precision and efficiency in answering user questions

## Example Use Cases

Your solution should handle queries like these (but not be limited to them):

1. **Installation Support:** "How can I install part number PS11752778?"
2. **Compatibility Checking:** "Is this part compatible with my WDT780SAEM1 model?"
3. **Troubleshooting:** "The ice maker on my Whirlpool fridge is not working. How can I fix it?"

## Resources Provided
- Front-end template (available in submission portal)
- Augmented Language Models PDF
- OpenAI's guide to prompt engineering

## Important Legal Notice

### Disclaimer – Use of Submitted Code and Materials

By participating in this case study interview, you acknowledge that:

- Any code, designs, documentation, or related materials ("Submitted Materials") you provide are **for evaluation purposes only**
- **InstaLily AI will NOT:**
  - Use, reproduce, distribute, or incorporate any Submitted Materials into products/services
  - Use materials for internal tools or commercial purposes
  - Retain materials beyond the evaluation period
- **You retain full ownership** and intellectual property rights to all Submitted Materials
- Materials will be reviewed **only by the hiring team** for assessment purposes
- **No IP rights transfer** occurs through participation in this interview

## Contact Information
For questions, please contact the hiring team through the submission portal.
* [Front-end Template](https://github.com/Instalily/case-study)
* [Augmented_Language_Models.pdf](https://cdn.sanity.io/files/facn3pk3/production/fd3e006c00fbee994421b83a5cfb5570c33b99e4.pdf)
* [OpenAI's guide to prompt engineering](https://platform.openai.com/docs/guides/prompt-engineering)
  
---

## Strategic Notes for Implementation

### Technical Architecture Considerations
- **Data Pipeline:** Web scraping PartSelect for refrigerator/dishwasher parts
- **Vector Database:** For efficient product similarity and search
- **Agent Framework:** Consider LangChain integration with DeepSeek
- **Real-time Features:** Live product availability, pricing updates
- **Security:** Proper data handling for customer transactions

### Differentiation Opportunities
- **Multi-modal Support:** Handle part images, diagrams, installation videos
- **Smart Recommendations:** Suggest complementary parts or tools
- **Proactive Assistance:** Detect common issues and offer solutions
- **Integration Ready:** Design for easy integration with PartSelect's existing systems

