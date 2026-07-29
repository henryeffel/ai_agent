import React, { useEffect, useState, useRef } from "react";
import ReactMarkdown from "react-markdown";

import {
  Box,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  Circle,
  Flex,
  Input,
} from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { useNavigate } from "react-router-dom";
import { FiMic, FiSquare, FiPause, FiPlay, FiSend } from "react-icons/fi";
import Card from "../components/Card";
import { useAppContext } from "../context/AppContext";
import * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";

// ▼▼▼ Azure 키 설정 (나중엔 .env로 빼세요) ▼▼▼
const SPEECH_KEY = import.meta.env.VITE_SPEECH_KEY;
const SPEECH_REGION = import.meta.env.VITE_SPEECH_REGION;

const API_URL = import.meta.env.VITE_API_URL;

const pulse = keyframes`
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.8; }
`;

function Meeting() {
  const navigate = useNavigate();
  const {
    currentMeeting,
    isRecording,
    recordingTime,
    setRecordingTime,
    stopRecording,
    setTranscript, // Context에 저장하는 함수
  } = useAppContext();

  const [isProcessing, setIsProcessing] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // ▼▼▼ [Real Tech] 실제 STT 데이터 저장용 ▼▼▼
  const [localTranscript, setLocalTranscript] = useState("");
  const recognizerRef = useRef(null); // SDK 객체 저장용

  const [aiMessages, setAiMessages] = useState([
    {
      type: "ai",
      text: "회의 중 궁금한 점이 있으면 물어보세요!",
      time: new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [aiInput, setAiInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);

  // --- [1] 페이지 로드 시 Azure 녹음기 시동 ---
  useEffect(() => {
    //  [핵심] 이미 녹음기가 켜져 있으면 또 켜지 말고 돌아가! (중복 방지)
    if (recognizerRef.current) return;
    if (!isRecording) return; // 녹음 상태가 아니면 시작 안 함 (선택 사항)

    let recognizer;

    try {
      // 키 확인 안전장치
      if (!SPEECH_KEY || SPEECH_KEY.includes("your_key_here")) {
        console.warn("⚠️ Azure Speech Key가 설정되지 않았습니다.");
        // 여기서 return 하면 시뮬레이션 모드라도 돌릴 수 있게 할지는 선택
        // return; 
      }

      const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(
        SPEECH_KEY || "dummy",
        SPEECH_REGION || "koreacentral"
      );
      speechConfig.speechRecognitionLanguage = "ko-KR";

      const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
      recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

      // [이벤트 1] 인식된 문장이 완성되었을 때 (Recognized)
      recognizer.recognized = (s, e) => {
        if (e.result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
          console.log("인식됨:", e.result.text);
          setLocalTranscript((prev) => prev + (prev ? "\n" : "") + e.result.text);
        }
      };

      // [이벤트 2] 실시간으로 인식 중일 때 (Recognizing) - 선택 구현
      // recognizer.recognizing = (s, e) => {
      //    console.log("인식 중:", e.result.text);
      // };

      recognizer.startContinuousRecognitionAsync(() => {
        console.log("🎙️ Azure 녹음 시작됨");
      });

      recognizerRef.current = recognizer;
    } catch (error) {
      console.error("❌ Azure SDK 초기화 오류:", error);
    }

    // 페이지 나갈 때 정리 (Cleanup)
    return () => {
      if (recognizer) {
        recognizer.stopContinuousRecognitionAsync(() => {
          recognizer.close(); // 자원 해제
        });
      }
      recognizerRef.current = null; // 초기화
    };
  }, [isRecording]); // isRecording이 true일 때 시작

  // --- 타이머 로직 ---
  useEffect(() => {
    let timer;
    if (isRecording && !isPaused) {
      timer = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isRecording, isPaused, setRecordingTime]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`;
  };

  const handlePauseResume = () => {
    setIsPaused(!isPaused);
    // 실제 SDK도 일시정지 기능을 지원하지만, 여기서는 단순 UI 상태 변경만 처리하고
    // 텍스트는 계속 받을지, 아니면 stopContinuousRecognitionAsync를 쓸지 선택해야 합니다.
    // 간단하게는 무시하겠습니다.
  };

  // ▼▼▼ [수정됨] 종료 버튼 클릭 시 로직 ▼▼▼
  const handleStopRecording = () => {
    stopRecording(); // Context 상태 변경
    setIsProcessing(true); // 로딩 화면 보여주기

    // Azure 녹음기 끄기
    if (recognizerRef.current) {
      recognizerRef.current.stopContinuousRecognitionAsync(() => {
        console.log("🛑 녹음 종료. 저장된 내용:", localTranscript);

        // [중요] 전역 Context에 녹음본 저장
        setTranscript(localTranscript);
        localStorage.setItem("lastTranscript", localTranscript);

        // 2초 후 결과 화면으로 이동
        setTimeout(() => {
          setIsProcessing(false);
          navigate("/result");
        }, 2000);
      });
    } else {
      // 혹시 녹음기가 안 켜졌을 경우 대비
      console.warn("녹음기가 초기화되지 않았습니다. 로컬 내용을 저장 후 이동합니다.");
      if (localTranscript) {
        setTranscript(localTranscript);
        localStorage.setItem("lastTranscript", localTranscript);
      }
      setTimeout(() => {
        setIsProcessing(false);
        navigate("/result");
      }, 2000);
    }
  };

  const handleAiSend = async () => {
    if (!aiInput.trim()) return;
    const userMessage = {
      type: "user",
      text: aiInput,
      time: new Date().toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setAiMessages((prev) => [...prev, userMessage]);
    const currentInput = aiInput;
    setAiInput("");
    setIsChatLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: currentInput,
          category: "all"
        }),
      });

      if (!response.ok) throw new Error("서버 응답 에러");

      const data = await response.json();

      const aiResponse = {
        type: "ai",
        text: data.response || data.answer,
        time: new Date().toLocaleTimeString("ko-KR", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setAiMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      console.error("Chat Error:", error);
      const errorMessage = {
        type: "ai",
        text: "죄송합니다. 서버 연결에 실패했습니다. 백엔드 상태를 확인해주세요.",
        time: new Date().toLocaleTimeString("ko-KR", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setAiMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsChatLoading(false);
    }
  };

  if (isProcessing) {
    return (
      <Box textAlign="center" py={20}>
        <VStack spacing={6}>
          <Circle
            size="100px"
            bg="primary.500"
            animation={`${pulse} 1.5s ease-in-out infinite`}
          >
            <FiMic size={40} color="white" />
          </Circle>
          <Heading size="lg" color="primary.500">
            회의록 생성 중...
          </Heading>
          <Text color="gray.600">
            AI가 회의 내용을 분석하고 정리하고 있습니다
          </Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Flex gap={6} py={8} px={4}>
      {/* 왼쪽: 메인 녹음 화면 */}
      <Box flex="1" maxW="700px">
        <Card textAlign="center">
          <VStack spacing={8}>
            {/* 녹음 중 애니메이션 */}
            <Circle
              size="150px"
              bg="red.500"
              animation={`${pulse} 2s ease-in-out infinite`}
            >
              <FiMic size={60} color="white" />
            </Circle>

            {/* 타이머 */}
            <VStack spacing={2}>
              <Heading size="2xl" color="red.500">
                {formatTime(recordingTime)}
              </Heading>
              <HStack>
                <Circle size="12px" bg={isPaused ? "orange.500" : "red.500"} />
                <Text fontSize="lg" color="gray.600">
                  {isPaused ? "일시정지 중" : "녹음 중"}
                </Text>
              </HStack>
            </VStack>

            {/* 일시정지 / 종료 버튼 */}
            <HStack spacing={4}>
              <Button
                size="lg"
                colorScheme={isPaused ? "green" : "orange"}
                leftIcon={isPaused ? <FiPlay /> : <FiPause />}
                onClick={handlePauseResume}
                w="150px"
                _hover={{ transform: "scale(1.05)" }}
                transition="all 0.2s"
              >
                {isPaused ? "재개" : "일시정지"}
              </Button>

              <Button
                size="lg"
                colorScheme="red"
                leftIcon={<FiSquare />}
                onClick={handleStopRecording}
                w="150px"
                _hover={{ transform: "scale(1.05)" }}
                transition="all 0.2s"
              >
                회의 종료
              </Button>
            </HStack>
          </VStack>
        </Card>

        {/* STT 실시간 전사 창 */}
        <Card mt={6}>
          <Heading size="sm" mb={3}>
            📝 실시간 전사 내용 (Azure STT)
          </Heading>
          <Box
            bg="gray.50"
            p={4}
            borderRadius="8px"
            h="calc(55vh - 150px)"
            overflowY="auto"
            border="1px solid"
            borderColor="gray.200"
          >
            {localTranscript ? (
              <Text fontSize="sm" color="gray.700" whiteSpace="pre-wrap">
                {localTranscript}
              </Text>
            ) : (
              <Text fontSize="sm" color="gray.500" fontStyle="italic">
                아직 대화 내용이 없습니다. 말씀을 시작하세요...
                <br />
                (Azure Key가 설정되었는지 확인해주세요)
              </Text>
            )}
          </Box>
        </Card>

        {/* 회의 정보 */}
        {currentMeeting && (
          <Card mt={6}>
            <Heading size="sm" mb={3}>
              📅 새 회의
            </Heading>
            <Box bg="gray.50" p={4} borderRadius="12px" w="full">
              <Text fontSize="lg" fontWeight="bold" mb={2}>
                {currentMeeting.title}
              </Text>
              <HStack justify="center" fontSize="sm" color="gray.600">
                <Text>{currentMeeting.date}</Text>
                <Text>·</Text>
                <Text>시작: {currentMeeting.startTime}</Text>
              </HStack>
            </Box>
          </Card>
        )}
      </Box>

      {/* 오른쪽: AI 비서 채팅창 */}
      <Box w="350px">
        <Card h="calc(100vh - 150px)" display="flex" flexDirection="column">
          <Heading size="sm" mb={4}>
            💬 이음 AI 비서
          </Heading>

          {/* 채팅 메시지 */}
          <Box
            flex="1"
            overflowY="auto"
            mb={4}
            p={2}
            bg="gray.50"
            borderRadius="8px"
          >
            <VStack spacing={3} align="stretch">
              {aiMessages.map((msg, idx) => (
                <Box
                  key={idx}
                  alignSelf={msg.type === "user" ? "flex-end" : "flex-start"}
                  maxW="85%"
                >
                  <Box
                    bg={msg.type === "user" ? "primary.500" : "white"}
                    color={msg.type === "user" ? "white" : "gray.800"}
                    p={3}
                    borderRadius="12px"
                    boxShadow="sm"
                  >
                    <Box
                                            fontSize="sm"
                                            sx={{
                                                "& p": { marginBottom: "0.5rem" },
                                                "& strong": {
                                                    fontWeight: "bold",
                                                    // 유저 메시지면 흰색 유지, AI 메시지면 보라색 포인트
                                                    color: msg.type === "user" ? "white" : "#4811BF",
                                                },
                                                "& ul": { paddingLeft: "1.2rem" },
                                                "& li": { marginBottom: "0.2rem" },
                                            }}
                                        >
                                            <ReactMarkdown>{msg.text}</ReactMarkdown>
                                        </Box>
                  </Box>
                  <Text
                    fontSize="xs"
                    color="gray.500"
                    mt={1}
                    textAlign={msg.type === "user" ? "right" : "left"}
                  >
                    {msg.time}
                  </Text>
                </Box>
              ))}
              {isChatLoading && (
                <Box alignSelf="flex-start" maxW="85%">
                  <Box bg="white" color="gray.500" p={3} borderRadius="12px" boxShadow="sm">
                    <Text fontSize="sm">이음 AI가 답변을 생각중입니다...</Text>
                  </Box>
                </Box>
              )}
            </VStack>
          </Box>

          {/* 입력 창 */}
          <HStack>
            <Input
              placeholder="질문을 입력하세요..."
              value={aiInput}
              onChange={(e) => setAiInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleAiSend()}
              size="sm"
              disabled={isChatLoading}
            />
            <Button
              colorScheme="primary"
              size="sm"
              leftIcon={<FiSend />}
              onClick={handleAiSend}
              isLoading={isChatLoading}
            >
              전송
            </Button>
          </HStack>
        </Card>
      </Box>
    </Flex>
  );
}

export default Meeting;
