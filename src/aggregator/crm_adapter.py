import json
import base64
from typing import Optional, List, Dict, Any, Tuple
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, Timeout, ConnectionError

from aggregator.model import Machine, User
from .clock import Time
from .model import history_line_to_json, json_to_history_line
from .utils import make_random_string


class CrmAdapter(object):
    def __init__(
        self,
        clock,
        base_url: str = "https://mijn.makerspaceleiden.nl/api/v1",
        auth_type: str = "token",  # "token" or "basic"
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize HTTP REST adapter for MakerSpace Leiden API.
        
        Args:
            clock: Clock instance for time operations
            base_url: Base URL for the REST API
            auth_type: Authentication type - "token" or "basic"
            api_token: API token for token-based auth
            username: Username for basic auth
            password: Password for basic auth
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            headers: Additional headers to include in requests
        """
        self.clock = clock
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        # Setup session with authentication
        self.session = requests.Session()
        
        # Set up authentication
        if auth_type == "token" and api_token:
            self.session.headers.update({
                'Authorization': f'Api-Key {api_token}'
            })
        elif auth_type == "basic" and username and password:
            self.session.auth = HTTPBasicAuth(username, password)
        else:
            raise ValueError("Invalid authentication configuration")
        
        # Set default headers
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Add custom headers if provided
        if headers:
            self.session.headers.update(headers)

        # Available endpoints
        self.endpoints = {
            'members': f"{self.base_url}/members/?format=json",
            'machines': f"{self.base_url}/machines/?format=json", 
            'member_checkins': f"{self.base_url}/members/?format=json"
        }

    def _make_request(self, method: str, url: str, data: Any = None, params: Dict = None, logger=None) -> Optional[Dict]:
        """Make HTTP request with error handling."""
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout, verify=self.verify_ssl)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params, timeout=self.timeout, verify=self.verify_ssl)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params, timeout=self.timeout, verify=self.verify_ssl)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, json=data, params=params, timeout=self.timeout, verify=self.verify_ssl)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, timeout=self.timeout, verify=self.verify_ssl)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return {}
            
            return [response.status_code, response.json()]
            
        except Timeout:
            if logger:
                logger.error(f"Request timeout for {method} {url}")
            return None
        except ConnectionError:
            if logger:
                logger.error(f"Connection error for {method} {url}")
            return None
        except RequestException as e:
            if logger:
                logger.error(f"Request failed for {method} {url}: {str(e)}")
            return None
        except json.JSONDecodeError:
            if logger:
                logger.error(f"Invalid JSON response from {method} {url}")
            return None
        
    def user_checkin(self, user_id, logger):
        logger = logger.getLogger(subsystem="crm")
        logger.info(f"Checking in user {user_id}")
        
        data = self._make_request('POST', self.base_url + f'/members/{user_id}/checkin/', data={}, logger=logger)
        if data:
            logger.info(f"Successfully checked in user {user_id}")
            return True
        else:
            logger.error(f"Failed to check in user {user_id}")
            return False