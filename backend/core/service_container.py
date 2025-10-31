"""
Service Container for Dependency Injection

This container manages the lifecycle and dependencies of all services,
enabling dependency injection and making services easily testable.
"""

from typing import Optional
from ..services.claude_service import ClaudeService
from ..services.storage_service import StorageService
from ..services.conversation_service import ConversationService
from ..services.rag_service import RAGService
from ..services.gladly_download_service import GladlyDownloadService
from ..utils.logging import get_logger

logger = get_logger('service_container')


class ServiceContainer:
    """
    Service container that manages service lifecycle and dependencies.
    
    This implements a singleton-like pattern where services are lazily
    initialized and cached. Services can be overridden for testing.
    """
    
    def __init__(self):
        """Initialize the service container"""
        # Core services
        self._storage_service: Optional[StorageService] = None
        self._claude_service: Optional[ClaudeService] = None
        self._conversation_service: Optional[ConversationService] = None
        self._rag_service: Optional[RAGService] = None
        self._gladly_download_service: Optional[GladlyDownloadService] = None
        
        # Track if services are overridden (for testing)
        self._overrides: dict = {}
        
        logger.info("Service container initialized")
    
    # Storage Service
    def get_storage_service(self, override: Optional[StorageService] = None) -> StorageService:
        """
        Get or create the StorageService instance.
        
        Args:
            override: Optional service instance to use instead (for testing)
            
        Returns:
            StorageService instance
        """
        if override is not None:
            self._overrides['storage_service'] = override
            self._storage_service = override
            return override
        
        if 'storage_service' in self._overrides:
            return self._overrides['storage_service']
        
        if self._storage_service is None:
            logger.debug("Creating StorageService instance")
            self._storage_service = StorageService()
        
        return self._storage_service
    
    # Claude Service
    def get_claude_service(self, override: Optional[ClaudeService] = None) -> Optional[ClaudeService]:
        """
        Get or create the ClaudeService instance.
        
        Args:
            override: Optional service instance to use instead (for testing)
            
        Returns:
            ClaudeService instance or None if initialization fails
        """
        if override is not None:
            self._overrides['claude_service'] = override
            self._claude_service = override
            return override
        
        if 'claude_service' in self._overrides:
            return self._overrides.get('claude_service')
        
        if self._claude_service is None:
            try:
                # Check API key status before attempting initialization
                from ..utils.config import Config
                api_key_status = Config.get_api_key_status()
                logger.debug(f"Attempting ClaudeService initialization - API key status: {api_key_status}")
                
                logger.debug("Creating ClaudeService instance")
                self._claude_service = ClaudeService()
                logger.info("ClaudeService initialized successfully")
            except ValueError as e:
                # ValueError means API key is missing - this is expected in some environments
                logger.warning(f"ClaudeService not initialized - API key not configured: {str(e)}")
                self._claude_service = None
            except Exception as e:
                # Other exceptions are unexpected
                logger.error(f"Failed to initialize ClaudeService: {str(e)}", exc_info=True)
                self._claude_service = None
        
        return self._claude_service
    
    # Conversation Service
    def get_conversation_service(self, override: Optional[ConversationService] = None) -> ConversationService:
        """
        Get or create the ConversationService instance.
        
        Args:
            override: Optional service instance to use instead (for testing)
            
        Returns:
            ConversationService instance
        """
        if override is not None:
            self._overrides['conversation_service'] = override
            self._conversation_service = override
            return override
        
        if 'conversation_service' in self._overrides:
            return self._overrides['conversation_service']
        
        if self._conversation_service is None:
            logger.debug("Creating ConversationService instance")
            storage_service = self.get_storage_service()
            self._conversation_service = ConversationService(storage_service=storage_service)
        
        return self._conversation_service
    
    # RAG Service
    def get_rag_service(self, override: Optional[RAGService] = None) -> Optional[RAGService]:
        """
        Get or create the RAGService instance.
        
        Requires ClaudeService and ConversationService to be available.
        
        Args:
            override: Optional service instance to use instead (for testing)
            
        Returns:
            RAGService instance or None if dependencies are unavailable
        """
        if override is not None:
            self._overrides['rag_service'] = override
            self._rag_service = override
            return override
        
        if 'rag_service' in self._overrides:
            return self._overrides.get('rag_service')
        
        if self._rag_service is None:
            claude_service = self.get_claude_service()
            if claude_service is None:
                logger.warning("RAGService not initialized - ClaudeService unavailable")
                return None
            
            conversation_service = self.get_conversation_service()
            logger.debug("Creating RAGService instance")
            self._rag_service = RAGService(claude_service, conversation_service)
        
        return self._rag_service
    
    # Gladly Download Service
    def get_gladly_download_service(self, override: Optional[GladlyDownloadService] = None) -> Optional[GladlyDownloadService]:
        """
        Get or create the GladlyDownloadService instance.
        
        Args:
            override: Optional service instance to use instead (for testing)
            
        Returns:
            GladlyDownloadService instance or None if initialization fails
        """
        if override is not None:
            self._overrides['gladly_download_service'] = override
            self._gladly_download_service = override
            return override
        
        if 'gladly_download_service' in self._overrides:
            return self._overrides.get('gladly_download_service')
        
        if self._gladly_download_service is None:
            try:
                logger.debug("Creating GladlyDownloadService instance")
                self._gladly_download_service = GladlyDownloadService()
            except Exception as e:
                logger.error(f"Failed to initialize GladlyDownloadService: {str(e)}")
                self._gladly_download_service = None
        
        return self._gladly_download_service
    
    def clear_overrides(self):
        """Clear all service overrides (useful for testing cleanup)"""
        self._overrides.clear()
        logger.debug("Service overrides cleared")
    
    def reset(self):
        """Reset all services (for testing)"""
        self._storage_service = None
        self._claude_service = None
        self._conversation_service = None
        self._rag_service = None
        self._gladly_download_service = None
        self._overrides.clear()
        logger.debug("Service container reset")

