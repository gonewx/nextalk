"""
Unit tests for recognition session management.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import time
import uuid
from datetime import datetime
from typing import Any

from nextalk.core.session import (
    RecognitionSession,
    SessionState,
    SessionMetrics
)


class TestSessionState(unittest.TestCase):
    """Test SessionState enum."""
    
    def test_session_states(self):
        """Test session state values."""
        self.assertEqual(SessionState.IDLE.value, "idle")
        self.assertEqual(SessionState.RECORDING.value, "recording")
        self.assertEqual(SessionState.PROCESSING.value, "processing")
        self.assertEqual(SessionState.INJECTING.value, "injecting")
        self.assertEqual(SessionState.COMPLETED.value, "completed")
        self.assertEqual(SessionState.CANCELLED.value, "cancelled")
        self.assertEqual(SessionState.ERROR.value, "error")


class TestSessionMetrics(unittest.TestCase):
    """Test SessionMetrics dataclass."""
    
    def test_create_metrics(self):
        """Test creating session metrics."""
        metrics = SessionMetrics(
            session_id="test_id",
            start_time=100.0,
            end_time=105.0,
            audio_duration=5.0,
            recognized_text="Test text",
            injected_successfully=True,
            error_message=None
        )
        
        self.assertEqual(metrics.session_id, "test_id")
        self.assertEqual(metrics.start_time, 100.0)
        self.assertEqual(metrics.end_time, 105.0)
        self.assertEqual(metrics.audio_duration, 5.0)
        self.assertEqual(metrics.recognized_text, "Test text")
        self.assertTrue(metrics.injected_successfully)
        self.assertIsNone(metrics.error_message)
    
    def test_metrics_with_error(self):
        """Test metrics with error."""
        metrics = SessionMetrics(
            session_id="error_session",
            start_time=100.0,
            end_time=101.0,
            audio_duration=1.0,
            recognized_text="",
            injected_successfully=False,
            error_message="Recognition failed"
        )
        
        self.assertFalse(metrics.injected_successfully)
        self.assertEqual(metrics.error_message, "Recognition failed")


class TestRecognitionSession(unittest.TestCase):
    """Test RecognitionSession class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.session = RecognitionSession()
    
    def test_init(self):
        """Test session initialization."""
        self.assertIsNotNone(self.session.session_id)
        self.assertEqual(self.session.state, SessionState.IDLE)
        self.assertIsNotNone(self.session.created_at)
        self.assertIsNone(self.session.started_at)
        self.assertIsNone(self.session.ended_at)
        self.assertEqual(len(self.session.audio_buffer), 0)
        self.assertEqual(self.session.recognized_text, "")
        self.assertIsNone(self.session.error_message)
        self.assertFalse(self.session.injection_completed)
        self.assertFalse(self.session.injection_successful)
    
    def test_session_id_unique(self):
        """Test session IDs are unique."""
        session1 = RecognitionSession()
        session2 = RecognitionSession()
        
        self.assertNotEqual(session1.session_id, session2.session_id)
    
    def test_start(self):
        """Test starting session."""
        with patch('time.time', return_value=100.0):
            self.session.start()
        
        self.assertEqual(self.session.state, SessionState.RECORDING)
        self.assertEqual(self.session.started_at, 100.0)
        self.assertEqual(len(self.session.audio_buffer), 0)
    
    def test_start_already_started(self):
        """Test starting already started session."""
        self.session.start()
        original_time = self.session.started_at
        
        # Try to start again
        self.session.start()
        
        # Should not change
        self.assertEqual(self.session.started_at, original_time)
    
    def test_stop(self):
        """Test stopping session."""
        self.session.start()
        
        with patch('time.time', return_value=105.0):
            self.session.stop()
        
        self.assertEqual(self.session.state, SessionState.PROCESSING)
        self.assertEqual(self.session.ended_at, 105.0)
    
    def test_stop_not_started(self):
        """Test stopping session that wasn't started."""
        self.session.stop()
        
        self.assertEqual(self.session.state, SessionState.IDLE)
        self.assertIsNone(self.session.ended_at)
    
    def test_cancel(self):
        """Test canceling session."""
        self.session.start()
        self.session.add_audio_data(b"test_data")
        
        with patch('time.time', return_value=102.0):
            self.session.cancel()
        
        self.assertEqual(self.session.state, SessionState.CANCELLED)
        self.assertEqual(self.session.ended_at, 102.0)
        self.assertEqual(len(self.session.audio_buffer), 0)  # Buffer cleared
    
    def test_add_audio_data(self):
        """Test adding audio data."""
        self.session.start()
        
        data1 = b"audio_chunk_1"
        data2 = b"audio_chunk_2"
        
        self.session.add_audio_data(data1)
        self.session.add_audio_data(data2)
        
        self.assertEqual(len(self.session.audio_buffer), 2)
        self.assertIn(data1, self.session.audio_buffer)
        self.assertIn(data2, self.session.audio_buffer)
    
    def test_add_audio_data_not_recording(self):
        """Test adding audio data when not recording."""
        data = b"test_data"
        
        self.session.add_audio_data(data)
        
        # Should not add data
        self.assertEqual(len(self.session.audio_buffer), 0)
    
    def test_get_audio_buffer(self):
        """Test getting audio buffer."""
        self.session.start()
        
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        for chunk in chunks:
            self.session.add_audio_data(chunk)
        
        combined = self.session.get_audio_buffer()
        
        self.assertEqual(combined, b"chunk1chunk2chunk3")
    
    def test_get_audio_buffer_empty(self):
        """Test getting empty audio buffer."""
        result = self.session.get_audio_buffer()
        
        self.assertEqual(result, b"")
    
    def test_process_recognition(self):
        """Test processing recognition result."""
        self.session.start()
        self.session.stop()
        
        text = "Recognized speech text"
        self.session.process_recognition(text)
        
        self.assertEqual(self.session.recognized_text, text)
        self.assertEqual(self.session.state, SessionState.INJECTING)
    
    def test_process_recognition_not_processing(self):
        """Test processing recognition when not in processing state."""
        text = "Test text"
        
        self.session.process_recognition(text)
        
        # Should not process
        self.assertEqual(self.session.recognized_text, "")
        self.assertEqual(self.session.state, SessionState.IDLE)
    
    def test_complete_injection_success(self):
        """Test completing successful injection."""
        self.session.start()
        self.session.stop()
        self.session.process_recognition("Test")
        
        with patch('time.time', return_value=110.0):
            self.session.complete_injection(success=True)
        
        self.assertEqual(self.session.state, SessionState.COMPLETED)
        self.assertTrue(self.session.injection_completed)
        self.assertTrue(self.session.injection_successful)
        self.assertEqual(self.session.ended_at, 110.0)
    
    def test_complete_injection_failure(self):
        """Test completing failed injection."""
        self.session.start()
        self.session.stop()
        self.session.process_recognition("Test")
        
        self.session.complete_injection(success=False)
        
        self.assertEqual(self.session.state, SessionState.ERROR)
        self.assertTrue(self.session.injection_completed)
        self.assertFalse(self.session.injection_successful)
    
    def test_report_error(self):
        """Test reporting error."""
        error_msg = "Network connection failed"
        
        with patch('time.time', return_value=103.0):
            self.session.report_error(error_msg)
        
        self.assertEqual(self.session.state, SessionState.ERROR)
        self.assertEqual(self.session.error_message, error_msg)
        self.assertEqual(self.session.ended_at, 103.0)
    
    def test_is_active(self):
        """Test checking if session is active."""
        # Idle - not active
        self.assertFalse(self.session.is_active())
        
        # Recording - active
        self.session.start()
        self.assertTrue(self.session.is_active())
        
        # Processing - active
        self.session.stop()
        self.assertTrue(self.session.is_active())
        
        # Injecting - active
        self.session.process_recognition("Test")
        self.assertTrue(self.session.is_active())
        
        # Completed - not active
        self.session.complete_injection(True)
        self.assertFalse(self.session.is_active())
    
    def test_get_duration(self):
        """Test getting session duration."""
        # Not started
        self.assertEqual(self.session.get_duration(), 0.0)
        
        # Started but not ended
        with patch('time.time', return_value=100.0):
            self.session.start()
        
        with patch('time.time', return_value=105.0):
            duration = self.session.get_duration()
        
        self.assertEqual(duration, 5.0)
        
        # Started and ended
        with patch('time.time', return_value=110.0):
            self.session.stop()
        
        duration = self.session.get_duration()
        self.assertEqual(duration, 10.0)  # 110 - 100
    
    def test_get_metrics(self):
        """Test getting session metrics."""
        # Complete successful session
        with patch('time.time', return_value=100.0):
            self.session.start()
        
        self.session.add_audio_data(b"audio1")
        self.session.add_audio_data(b"audio2")
        
        with patch('time.time', return_value=105.0):
            self.session.stop()
        
        self.session.process_recognition("Test recognition")
        self.session.complete_injection(True)
        
        metrics = self.session.get_metrics()
        
        self.assertEqual(metrics.session_id, self.session.session_id)
        self.assertEqual(metrics.start_time, 100.0)
        self.assertEqual(metrics.end_time, 105.0)
        self.assertEqual(metrics.audio_duration, 5.0)
        self.assertEqual(metrics.recognized_text, "Test recognition")
        self.assertTrue(metrics.injected_successfully)
        self.assertIsNone(metrics.error_message)
    
    def test_get_metrics_with_error(self):
        """Test getting metrics for error session."""
        self.session.start()
        self.session.report_error("Recognition failed")
        
        metrics = self.session.get_metrics()
        
        self.assertFalse(metrics.injected_successfully)
        self.assertEqual(metrics.error_message, "Recognition failed")
    
    def test_set_callbacks(self):
        """Test setting callbacks."""
        on_state_change = Mock()
        on_text_recognized = Mock()
        on_error = Mock()
        on_complete = Mock()
        
        self.session.set_on_state_change(on_state_change)
        self.session.set_on_text_recognized(on_text_recognized)
        self.session.set_on_error(on_error)
        self.session.set_on_complete(on_complete)
        
        self.assertEqual(self.session._on_state_change, on_state_change)
        self.assertEqual(self.session._on_text_recognized, on_text_recognized)
        self.assertEqual(self.session._on_error, on_error)
        self.assertEqual(self.session._on_complete, on_complete)
    
    def test_state_change_callback(self):
        """Test state change callback."""
        callback = Mock()
        self.session.set_on_state_change(callback)
        
        self.session.start()
        
        callback.assert_called_once_with(SessionState.RECORDING)
    
    def test_text_recognized_callback(self):
        """Test text recognized callback."""
        callback = Mock()
        self.session.set_on_text_recognized(callback)
        
        self.session.start()
        self.session.stop()
        self.session.process_recognition("Test text")
        
        callback.assert_called_once_with("Test text")
    
    def test_error_callback(self):
        """Test error callback."""
        callback = Mock()
        self.session.set_on_error(callback)
        
        self.session.report_error("Test error")
        
        callback.assert_called_once_with("Test error")
    
    def test_complete_callback(self):
        """Test completion callback."""
        callback = Mock()
        self.session.set_on_complete(callback)
        
        self.session.start()
        self.session.stop()
        self.session.process_recognition("Test")
        self.session.complete_injection(True)
        
        callback.assert_called_once()
        metrics = callback.call_args[0][0]
        self.assertIsInstance(metrics, SessionMetrics)
        self.assertTrue(metrics.injected_successfully)
    
    def test_callback_error_handling(self):
        """Test callback error doesn't break session."""
        bad_callback = Mock(side_effect=Exception("Callback error"))
        self.session.set_on_state_change(bad_callback)
        
        # Should not raise exception
        self.session.start()
        
        self.assertEqual(self.session.state, SessionState.RECORDING)
        bad_callback.assert_called_once()


class TestSessionIntegration(unittest.TestCase):
    """Test session integration scenarios."""
    
    def test_complete_session_flow(self):
        """Test complete session flow."""
        session = RecognitionSession()
        
        # Setup callbacks
        state_changes = []
        recognized_texts = []
        errors = []
        completions = []
        
        session.set_on_state_change(lambda s: state_changes.append(s))
        session.set_on_text_recognized(lambda t: recognized_texts.append(t))
        session.set_on_error(lambda e: errors.append(e))
        session.set_on_complete(lambda m: completions.append(m))
        
        # Run session
        session.start()
        self.assertIn(SessionState.RECORDING, state_changes)
        
        # Add audio
        for i in range(5):
            session.add_audio_data(f"chunk_{i}".encode())
        
        # Stop recording
        session.stop()
        self.assertIn(SessionState.PROCESSING, state_changes)
        
        # Process recognition
        session.process_recognition("Hello world")
        self.assertIn(SessionState.INJECTING, state_changes)
        self.assertIn("Hello world", recognized_texts)
        
        # Complete injection
        session.complete_injection(True)
        self.assertIn(SessionState.COMPLETED, state_changes)
        
        # Check metrics
        self.assertEqual(len(completions), 1)
        metrics = completions[0]
        self.assertEqual(metrics.recognized_text, "Hello world")
        self.assertTrue(metrics.injected_successfully)
        self.assertEqual(len(errors), 0)
    
    def test_error_session_flow(self):
        """Test session flow with error."""
        session = RecognitionSession()
        
        errors = []
        session.set_on_error(lambda e: errors.append(e))
        
        session.start()
        session.add_audio_data(b"audio_data")
        
        # Simulate error
        session.report_error("Network timeout")
        
        self.assertEqual(session.state, SessionState.ERROR)
        self.assertIn("Network timeout", errors)
        
        # Check metrics
        metrics = session.get_metrics()
        self.assertFalse(metrics.injected_successfully)
        self.assertEqual(metrics.error_message, "Network timeout")
    
    def test_cancelled_session_flow(self):
        """Test cancelled session flow."""
        session = RecognitionSession()
        
        session.start()
        session.add_audio_data(b"audio1")
        session.add_audio_data(b"audio2")
        
        # Cancel session
        session.cancel()
        
        self.assertEqual(session.state, SessionState.CANCELLED)
        self.assertEqual(len(session.audio_buffer), 0)
        
        # Try to process - should not work
        session.process_recognition("Should not process")
        self.assertEqual(session.recognized_text, "")
    
    def test_multiple_sessions(self):
        """Test managing multiple sessions."""
        sessions = []
        
        # Create multiple sessions
        for i in range(5):
            session = RecognitionSession()
            session.start()
            session.add_audio_data(f"session_{i}".encode())
            session.stop()
            session.process_recognition(f"Text {i}")
            session.complete_injection(i % 2 == 0)  # Alternate success/failure
            sessions.append(session)
        
        # Check results
        successful = [s for s in sessions if s.injection_successful]
        failed = [s for s in sessions if not s.injection_successful and s.injection_completed]
        
        self.assertEqual(len(successful), 3)  # 0, 2, 4
        self.assertEqual(len(failed), 2)  # 1, 3
        
        # Check all have unique IDs
        ids = [s.session_id for s in sessions]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == '__main__':
    unittest.main()