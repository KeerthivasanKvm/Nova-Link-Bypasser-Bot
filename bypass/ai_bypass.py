"""
AI Bypass
=========
AI-powered bypass using LLM for adaptive scraping.
Based on: https://github.com/Shubhamsaboo/awesome-llm-apps
"""

import json
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from openai import AsyncOpenAI

from bypass.base_bypass import BaseBypass, BypassResult, BypassStatus, register_bypass
from config import ai_config
from utils.logger import get_logger

logger = get_logger(__name__)


@register_bypass
class AIBypass(BaseBypass):
    """
    AI-powered bypass method.
    Uses LLM to:
    - Analyze page structure
    - Identify bypass patterns
    - Generate extraction strategies
    - Adapt to new protection methods
    """
    
    METHOD_NAME = "ai_powered"
    PRIORITY = 6
    TIMEOUT = 120
    
    def __init__(self):
        super().__init__()
        self.client: Optional[AsyncOpenAI] = None
        if ai_config.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=ai_config.OPENAI_API_KEY)
    
    async def bypass(self, url: str) -> BypassResult:
        """
        Attempt AI-powered bypass.
        
        Args:
            url: URL to bypass
            
        Returns:
            BypassResult
        """
        start_time = time.time()
        
        # Check if AI is configured
        if not self.client:
            return BypassResult.failed_result(
                error_message="AI not configured",
                method=self.METHOD_NAME,
                execution_time=time.time() - start_time,
                status=BypassStatus.UNSUPPORTED
            )
        
        try:
            logger.info(f"[AI] Attempting bypass for: {url}")
            
            # Fetch page content
            page_content = await self._fetch_page(url)
            if not page_content:
                execution_time = time.time() - start_time
                return BypassResult.failed_result(
                    error_message="Failed to fetch page",
                    method=self.METHOD_NAME,
                    execution_time=execution_time
                )
            
            # Analyze with AI
            result = await self._analyze_with_ai(url, page_content)
            
            if result and result.get('success'):
                bypass_url = result.get('url')
                if bypass_url and self._is_valid_url(bypass_url):
                    execution_time = time.time() - start_time
                    logger.info(f"[AI] Bypass successful: {bypass_url}")
                    return BypassResult.success_result(
                        url=bypass_url,
                        method=self.METHOD_NAME,
                        execution_time=execution_time,
                        metadata={
                            'technique': 'ai_analysis',
                            'confidence': result.get('confidence', 0),
                            'reasoning': result.get('reasoning', '')
                        }
                    )
            
            execution_time = time.time() - start_time
            return BypassResult.failed_result(
                error_message=result.get('error', 'AI analysis failed') if result else 'No result',
                method=self.METHOD_NAME,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[AI] Error: {e}")
            return BypassResult.failed_result(
                error_message=str(e),
                method=self.METHOD_NAME,
                execution_time=execution_time,
                status=BypassStatus.ERROR
            )
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch page content.
        
        Args:
            url: URL to fetch
            
        Returns:
            Page content or None
        """
        try:
            session = requests.Session()
            session.headers.update(self.headers)
            
            response = session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to fetch page: {e}")
            return None
    
    async def _analyze_with_ai(
        self,
        url: str,
        page_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze page with AI to find bypass method.
        
        Args:
            url: Original URL
            page_content: HTML content
            
        Returns:
            Analysis result or None
        """
        try:
            # Truncate content if too long
            max_content_length = 8000
            if len(page_content) > max_content_length:
                page_content = page_content[:max_content_length] + "..."
            
            # Prepare prompt
            system_prompt = """You are an expert web scraping and bypass specialist. Your task is to analyze HTML content from link shortener pages and extract the final destination URL.

Analyze the provided HTML and:
1. Identify what type of protection is being used (countdown, CAPTCHA, hidden elements, JavaScript obfuscation, etc.)
2. Look for any hidden URLs in the HTML, JavaScript, or meta tags
3. Identify patterns that might reveal the destination URL
4. Provide the final destination URL if found

Respond in JSON format with these fields:
- success: boolean indicating if you found the destination URL
- url: the destination URL (if success is true)
- confidence: number from 0-1 indicating confidence level
- reasoning: brief explanation of how you found the URL
- protection_type: type of protection detected
- error: error message (if success is false)

Be thorough in your analysis. Look for:
- Hidden form inputs with URLs
- JavaScript variables containing URLs
- Base64 encoded strings
- Data attributes on elements
- Comments containing URLs
- Obfuscated JavaScript
"""
            
            user_prompt = f"""URL: {url}

HTML Content:
```html
{page_content}
```

Analyze this page and extract the destination URL. Respond in JSON format only."""
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=ai_config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=ai_config.AI_TEMPERATURE,
                max_tokens=ai_config.AI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            logger.debug(f"AI analysis result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None
    
    async def generate_bypass_strategy(
        self,
        url: str,
        page_content: str,
        previous_attempts: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a bypass strategy using AI.
        
        Args:
            url: URL to bypass
            page_content: Page content
            previous_attempts: List of previously tried methods
            
        Returns:
            Strategy dict or None
        """
        try:
            system_prompt = """You are a web scraping expert. Generate a bypass strategy for the given protected page.

Respond in JSON format with:
- strategy: description of the approach
- selectors: list of CSS selectors to try
- actions: list of actions to perform (click, wait, fill, etc.)
- expected_result: what to look for as success
"""
            
            user_prompt = f"""URL: {url}
Previously tried: {', '.join(previous_attempts)}

HTML Content:
```html
{page_content[:5000]}
```

Generate a bypass strategy."""
            
            response = await self.client.chat.completions.create(
                model=ai_config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            return None
    
    async def learn_from_success(
        self,
        url: str,
        page_content: str,
        success_method: str,
        destination_url: str
    ) -> None:
        """
        Learn from successful bypass for future use.
        
        Args:
            url: Original URL
            page_content: Page content
            success_method: Method that worked
            destination_url: Final URL
        """
        try:
            # This could be extended to store patterns in database
            # for future similar sites
            logger.info(f"[AI] Learned: {success_method} worked for {self._extract_domain(url)}")
            
        except Exception as e:
            logger.error(f"Learning failed: {e}")
