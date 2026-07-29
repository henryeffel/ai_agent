import React, { useState, useEffect } from "react";
import {
  Box,
  Heading,
  Text,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  VStack,
  HStack,
  Badge,
  Divider,
  Button,
  Spinner,
  SimpleGrid,
  useToast,
} from "@chakra-ui/react";
import {
  FiFileText,
  FiTrendingUp,
  FiCheckCircle,
  FiDownload,
} from "react-icons/fi";
import Card from "../components/Card";
import ApprovalCenter from "../components/ApprovalCenter";
import { mockMeetingResult } from "../data/mockData";
import axios from "axios";
import { useAppContext } from "../context/AppContext";

const API_URL = import.meta.env.VITE_API_URL;

function Result() {
  // 1. 필수 상태 변수들
  const [tabIndex, setTabIndex] = useState(0);
  const { transcript, setAiSummary, aiSummary } = useAppContext();
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [realSummary, setRealSummary] = useState("");
  const [resultData, setResultData] = useState(mockMeetingResult); // 기본값 설정
  const toast = useToast();

  // 2. 페이지 진입 시 AI 분석 요청
  useEffect(() => {
    const processMeeting = async () => {
      // [핵심] localStorage에서 직접 읽기 (Context보다 먼저 로드됨)
      let savedTranscript =
        localStorage.getItem("lastTranscript") || transcript;

      // [테스트용] localStorage가 비어있으면 테스트 데이터 자동 주입
      if (!savedTranscript) {
        console.log("🧪 테스트 모드: 샘플 스크립트 주입");
        savedTranscript = `[박훈용] 좋습니다, 모두 모이셨네요. 오늘 회의 시작하겠습니다. 1월 12일 최종 발표까지 일주일 남았습니다. 오늘은 각 파트별 완성도 점검하고 발표 당일 역할 분담을 확정하겠습니다. 먼저 프론트엔드부터 확인할게요. 성태 님, 대시보드 상태는 어때요?
[김성태] 프론트엔드는 거의 완료됐습니다. STT 실시간 전사 창, 이음 AI 채팅창, 자동화 승인 센터까지 정상 작동 중입니다. 다만 RAG 업로드 탭이 3개 섹션으로 분리되면서 파일 크기 제한 검증 로직을 추가했는데, 백엔드와 한 번 더 테스트가 필요합니다. 현재 진행률은 90%입니다.
[박훈용] 알겠습니다. 백엔드 쪽은 어떻습니까? 채헌 님, STT 엔진 상태 먼저 말씀해주시죠.
[공채헌] Whisper 모델은 안정적입니다. 화자 분리 정확도는 95% 수준이고, 한국어/영어 혼용도 문제없습니다. 발표 당일 시연용 회의 시나리오는 실제로 ‘이음 서비스 기획 회의’ 내용을 녹음하면 리얼하게 보일 것 같습니다. 현재 진행률은 95%입니다.
[박지성] RAG 엔진 쪽에서 걱정이 있습니다. 과거 회의 데이터가 벡터 DB에 20건 정도뿐이라 시연에서 “저번 달 회의 내용 비교해줘” 같은 질문을 하려면 샘플 데이터를 더 넣어야 합니다. 특히 “12월 5일 전략회의”처럼 구체 날짜를 레퍼런스로 쓰려면 해당 회의록을 RAG에 미리 임베딩해야 합니다.
[박훈용] 좋습니다. 오늘 회의 끝나고 지성 님이 샘플 회의록 3~4개 더 만들어서 RAG에 넣어주세요. 데드라인은 1월 9일까지로 하겠습니다.
[전혜나] 자동화 파이프라인은 정상 작동 중입니다. Outlook 일정 등록, 회의록 메일 발송, TO-DO LIST 생성까지 테스트 완료했습니다. 발표 당일 실제 Outlook 일정 등록을 보여주려면 참석자 이메일 계정을 미리 세팅해야 하는데, 데모용 계정을 만들까요 아니면 실제 계정을 쓸까요?
[박훈용] 개인정보 노출 위험이 있으니 데모용 더미 계정 3개 정도 만들어서 쓰는 게 안전하겠습니다. 혜나 님이 1월 11일까지 세팅 부탁드릴게요.
[고영후] 프롬프트 최적화는 완료됐고 GPT-5mini 기반으로 회의 요약 정확도는 98% 수준입니다. 책임 있는 AI 파트에서 PII 마스킹 기능을 시연에 포함시키면 임팩트가 있을 것 같습니다. 주민번호/전화번호 같은 민감 정보가 자동으로 가려지는 걸 보여주는 방식입니다. 진행률은 95% 정도입니다.
[박훈용] 좋습니다. 회의 스크립트에 전화번호나 이메일 같은 정보를 일부러 넣어서 마스킹되는 모습을 보여주세요. 영후 님이 시연 시나리오에 그 부분 추가해주시고요.
[박훈용] 발표 당일 역할 분담 정리하겠습니다. 저는 오프닝/문제 정의/핵심 가치. 성태 님은 시장 분석/차별화. 채헌 님은 STT 기능. 지성 님은 RAG 시스템. 혜나 님은 자동화. 영후 님은 책임 있는 AI 및 시연 영상 소개를 맡아주세요.
[김성태] 네, 알겠습니다. 시연 영상은 누가 촬영하고 편집하나요?
[박훈용] 촬영은 제가 하고, 성태 님이 편집 맡아주세요. 총 2분 15초 분량으로 실시간 STT 45초, RAG 질의응답 45초, 자동화 실행 45초로 3파트로 나눕니다. 촬영은 1월 11일 오전, 편집은 1월 11일 오후까지 완료 부탁드립니다.
[박지성] 발표 당일 라이브 시연도 하나요, 아니면 녹화 영상만 보여주나요? 라이브는 임팩트가 있지만 네트워크 이슈 리스크가 있습니다.
[박훈용] 녹화 영상 메인으로 가되, 라이브 시연은 플랜 B로 준비하겠습니다. 심사위원 요청 시 라이브로 보여주는 방식으로요. 발표장 와이파이 상태 사전 체크가 필요합니다. 성태 님, 1월 5일 리허설 때 네트워크 속도 테스트 부탁드립니다.
[김성태] 네, 알겠습니다.
[박훈용] 오늘 액션 아이템 정리합니다. 지성 님은 1월 9일까지 RAG 샘플 데이터 추가. 혜나 님은 1월 11일까지 데모용 Outlook 계정 세팅. 영후 님은 PII 마스킹 시연 시나리오 추가. 저와 성태 님은 1월 11일 시연 영상 촬영 및 편집 완료. 성태 님은 1월 5일 발표장 네트워크 테스트. 모두 이상 없으시죠?
[전원] 네, 확인했습니다!
[박훈용] 혜나님 진행률은 어떻게 되시죠?
[전혜나] 70%입니다.
[박훈용] 좋습니다. 그럼 각자 맡은 파트 마무리하고, 1월 12일 발표 때 최고의 퍼포먼스 보여줍시다. 수고하셨습니다!`;
        localStorage.setItem("lastTranscript", savedTranscript);
      }

      console.log(
        "🔍 savedTranscript:",
        savedTranscript.substring(0, 50) + "..."
      );

      try {
        console.log(" API 호출 중...");
        const response = await axios.post(`${API_URL}/analyze-meeting`, {
          summary_text: savedTranscript,
        });

        console.log("✅ API 응답:", response.data);

        if (response.data.status === "success") {
          const aiData = response.data.data;

          // [디버깅] AI가 반환한 데이터 상세 확인
          console.log("🤖 AI 전체 응답:", JSON.stringify(aiData, null, 2));
          console.log("📅 followUpMeeting:", aiData.followUpMeeting);
          console.log("📋 actionItems:", aiData.actionItems);

          // [핵심] ApprovalCenter가 터지지 않게 데이터 강제 주입
          const safeActionItems = Array.isArray(aiData.actionItems)
            ? aiData.actionItems
            : [];

          // [수정] Todo 항목들을 하나의 그룹화된 카드로 생성
          const safeApprovalItems = [];

          // [1] 후속 회의 일정 카드 생성 (AI가 추출했거나, 기본값 사용)
          const followUp = aiData.followUpMeeting || {};

          console.log("📆 followUp 객체:", followUp);
          console.log("📆 followUp.date:", followUp.date);
          console.log("📆 followUp.time:", followUp.time);

          // 회의 스크립트에서 참석자 이름 추출 (대괄호 안의 이름들)
          const extractedNames = [
            ...new Set(
              (savedTranscript.match(/\[([^\]]+)\]/g) || []).map((match) =>
                match.replace(/[\[\]]/g, "")
              )
            ),
          ];

          safeApprovalItems.push({
            id: "approval-calendar",
            type: "calendar",
            title: "Outlook 일정 등록",
            description: "다음 회의 일정을 자동으로 등록합니다",
            estimatedTime: "2초",
            details: {
              title: followUp.title || "후속 회의",
              date:
                followUp.date ||
                new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
                  .toISOString()
                  .split("T")[0], // 기본: 1주일 후
              time: followUp.time || "14:00",
              attendees:
                followUp.attendees?.length > 0
                  ? followUp.attendees
                  : extractedNames,
            },
          });

          // [2] 메일 발송 카드 추가 - 이메일 최적화 HTML
          // 할 일 목록 생성
          let actionItemsHtml = "";
          if (safeActionItems.length > 0) {
            actionItemsHtml =
              '<h3 style="color:#4811BF;margin-top:25px;margin-bottom:15px;">📋 할 일 목록</h3>';
            safeActionItems.forEach((item, idx) => {
              actionItemsHtml +=
                '<div style="background:#faf5ff;border-left:4px solid #8C5CF2;padding:12px 15px;margin-bottom:10px;border-radius:0 8px 8px 0;">';
              actionItemsHtml +=
                '<div style="font-weight:bold;color:#333;">' +
                (idx + 1) +
                ". " +
                (item.task || "할 일") +
                "</div>";
              actionItemsHtml +=
                '<div style="margin-top:8px;font-size:14px;color:#666;">';
              actionItemsHtml +=
                '👤 <strong style="color:#4811BF;">' +
                (item.assignee || "미정") +
                "</strong>";
              actionItemsHtml += " &nbsp;|&nbsp; ";
              actionItemsHtml +=
                '📅 <span style="color:#e53e3e;font-weight:bold;">' +
                (item.deadline || "추후 협의") +
                "</span>";
              actionItemsHtml += "</div></div>";
            });
          }

          // 결정사항 생성
          let decisionsHtml = "";
          if (Array.isArray(aiData.decisions) && aiData.decisions.length > 0) {
            decisionsHtml =
              '<h3 style="color:#4811BF;margin-top:20px;">✅ 주요 결정사항</h3>';
            decisionsHtml += '<ul style="margin:10px 0;padding-left:20px;">';
            aiData.decisions.forEach((d) => {
              decisionsHtml += '<li style="margin:5px 0;">' + d + "</li>";
            });
            decisionsHtml += "</ul>";
          }

          // 후속 회의 생성
          let nextMeetingHtml = "";
          if (followUp.date) {
            const attendeesList = (followUp.attendees || extractedNames)
              .map(
                (name) => '<strong style="color:#4811BF;">' + name + "</strong>"
              )
              .join(", ");

            nextMeetingHtml =
              '<h3 style="color:#4811BF;margin-top:20px;">📅 다음 회의</h3>';
            nextMeetingHtml +=
              '<div style="background:#f0f9ff;padding:15px;border-radius:8px;">';
            nextMeetingHtml +=
              "<strong>" + (followUp.title || "후속 회의") + "</strong><br>";
            nextMeetingHtml +=
              '일시: <strong style="color:#2563eb;">' +
              followUp.date +
              " " +
              (followUp.time || "") +
              "</strong><br>";
            nextMeetingHtml += "참석자: " + attendeesList;
            nextMeetingHtml += "</div>";
          }

          // 최종 이메일 본문 조립
          const summaryText = (aiData.summary || "").replace(/\n/g, "<br>");
          const formattedEmailBody =
            '<h2 style="color:#4811BF;">📝 회의 요약</h2>' +
            '<p style="line-height:1.8;color:#333;">' +
            summaryText +
            "</p>" +
            decisionsHtml +
            actionItemsHtml +
            nextMeetingHtml;

          safeApprovalItems.push({
            id: "approval-email",
            type: "email",
            title: "회의록 메일 발송",
            description: "참석자 전원에게 회의록을 자동 발송합니다",
            estimatedTime: "3초",
            details: {
              recipients: extractedNames,
              subject: `[이음] ${followUp.title || "회의"} - 회의록`,
              preview: `안녕하세요, ${new Date().toLocaleDateString()} 진행된 회의록을 공유드립니다...`,
              body: formattedEmailBody,
            },
          });

          // [3] Todo 항목들을 하나의 카드로 통합
          if (safeActionItems.length > 0) {
            safeApprovalItems.push({
              id: "approval-todo",
              type: "todo",
              title: "TO-DO LIST 등록",
              description: "담당자별 TO-DO LIST를 Outlook에 자동 등록합니다",
              estimatedTime: "2초",
              details: {
                count: safeActionItems.length,
                assignees: [
                  ...new Set(
                    safeActionItems.map((item) => item.assignee || "미정")
                  ),
                ],
                todoItems: safeActionItems.map((item) => ({
                  task: item.task || "할 일 내용 없음",
                  assignee: item.assignee || "미정",
                  deadline: item.deadline || "추후 협의",
                })),
              },
            });
          }

          // [4] 자동 보고 카드 추가
          safeApprovalItems.push({
            id: "approval-report",
            type: "report",
            title: "자동 보고",
            description:
              "회의록과 심층 분석 내용을 상사에게 자동으로 보고합니다",
            estimatedTime: "3초",
            details: {
              recipient: "김사장 (상사)",
              contents: [
                "회의록 요약",
                "심층 분석",
                "리스크 분석",
                "AI 추천사항",
              ],
            },
          });

          console.log("📋 생성된 approvalItems:", safeApprovalItems);

          // 데이터 병합 - mockMeetingResult 없이 AI 데이터만 사용
          const mergedData = {
            title: "AI 분석 완료된 회의",
            date: new Date().toLocaleDateString(),
            transcript: savedTranscript,
            summary: aiData.summary || "",

            // 배열 안전장치
            decisions: Array.isArray(aiData.decisions) ? aiData.decisions : [],
            actionItems: safeActionItems,
            openIssues: Array.isArray(aiData.openIssues)
              ? aiData.openIssues
              : [],
            approvalItems: safeApprovalItems,

            insights: {
              meetingType: aiData.insights?.meetingType || "일반 회의",
              sentiment: aiData.insights?.sentiment || "중립",
              keyTopics: Array.isArray(aiData.insights?.keyTopics)
                ? aiData.insights.keyTopics
                : [],
              risks: Array.isArray(aiData.insights?.risks)
                ? aiData.insights.risks
                : [],
              recommendations: Array.isArray(aiData.insights?.recommendations)
                ? aiData.insights.recommendations
                : [],
            },
          };

          console.log("📊 최종 mergedData:", mergedData);

          setResultData(mergedData);
          setRealSummary(aiData.summary);
          setAiSummary(aiData.summary);

          toast({ title: "분석 완료", status: "success", duration: 3000 });
        }
      } catch (error) {
        console.error("분석 에러:", error);
        toast({
          title: "분석 실패",
          description: "서버 연결 확인 필요",
          status: "error",
        });
      } finally {
        setIsLoading(false); // 무조건 로딩 끔
      }
    };

    processMeeting();
  }, [transcript]);

  // 3. 메일 발송 함수
  const handleSendEmail = async () => {
    if (!realSummary) {
      toast({ title: "내용 없음", status: "warning" });
      return;
    }
    try {
      // ApprovalCenter 내부에서 로딩을 관리하므로 여기선 상태 변경 X
      const response = await axios.post(`${API_URL}/execute-action`, {
        summary_text: realSummary,
      });
      if (response.data.status === "success") {
        console.log("메일 발송 성공");
        return true;
      }
    } catch (error) {
      console.error("메일 발송 에러:", error);
      throw error; // 에러를 던져야 자식 컴포넌트가 실패 처리를 함
    }
  };

  // 회의록 다운로드 함수 (Merged from be2_rag)
  const handleDownloadMinutes = async () => {
    // 1. 사용자 피드백 (로딩 토스트)
    toast({
      title: "회의록 생성 시작",
      description: "AI가 템플릿(스타일)을 확인하고 내용을 작성 중입니다...",
      status: "loading",
      duration: null, // 처리될 때까지 유지
      isClosable: false,
    });

    try {
      // 2. 현재 회의 데이터를 텍스트 컨텍스트로 변환 (LLM이 이해하기 좋은 형태로)
      const summaryContext = `
회의명: ${resultData.title || "팀 프로젝트 회의"}
회의 일시: ${resultData.date || new Date().toLocaleDateString()}
참석자: ${
        resultData.approvalItems?.[0]?.details?.recipients?.join(", ") ||
        "참석자"
      }
회의 목적: 프로젝트 구체화 작업 및 역할 분담, 개발 착수 논의

1. 회의 주요 내용
${realSummary || resultData.summary}

2. 향후 계획 및 일정
${
  resultData.actionItems
    ?.map((item) => `- ${item.task} (${item.assignee})`)
    .join("\n") || "없음"
}
        `;

      // 3. 백엔드 요청
      const response = await fetch(`${API_URL}/generate-minutes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ summary_text: summaryContext }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "생성 실패");
      }

      // 4. Blob 응답 처리 (파일 다운로드)
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      // Use resultData.title for filename
      link.setAttribute("download", `이음_회의록_${resultData.title}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);

      // 5. 성공 토스트
      toast.closeAll();
      toast({
        title: "다운로드 완료!",
        description: "Custom 회의록이 생성되었습니다.",
        status: "success",
        duration: 3000,
      });
    } catch (error) {
      console.error("Download Error:", error);
      toast.closeAll();
      toast({
        title: "생성 실패",
        description: "회의록 생성 중 오류가 발생했습니다.",
        status: "error",
        duration: 4000,
      });
    }
  };

  // TO-DO LIST 편집 저장
  const handleSaveTodoList = () => {
    setTodoList([...editedTodoList]);
    setIsEditingTodo(false);
    toast({
      title: "TO-DO LIST 저장 완료",
      description: "변경사항이 저장되었습니다.",
      status: "success",
      duration: 2000,
      isClosable: true,
    });
  };

  // TO-DO LIST 편집 취소
  const handleCancelTodoEdit = () => {
    setEditedTodoList([...todoList]);
    setIsEditingTodo(false);
  };

  // TO-DO 항목 수정
  const handleTodoChange = (index, field, value) => {
    const updated = [...editedTodoList];
    updated[index] = { ...updated[index], [field]: value };
    setEditedTodoList(updated);
  };

  // TO-DO 항목 추가
  const handleAddTodo = () => {
    setEditedTodoList([
      ...editedTodoList,
      {
        task: "새 작업",
        assignee: "담당자",
        deadline: "2025-12-31",
        status: "pending",
      },
    ]);
  };

  // TO-DO 항목 삭제
  const handleDeleteTodo = (index) => {
    const updated = editedTodoList.filter((_, i) => i !== index);
    setEditedTodoList(updated);
  };

  // TO-DO LIST 메일 발송
  const handleSendTodoEmail = () => {
    toast({
      title: "TO-DO LIST 메일 발송",
      description: "TO-DO LIST가 담당자들에게 메일로 발송되었습니다.",
      status: "success",
      duration: 3000,
      isClosable: true,
    });
  };

  // 4. 화면 렌더링
  return (
    <Box>
      {/* 헤더 */}
      <Card mb={6} bg="linear-gradient(135deg, #4811BF 0%, #8C5CF2 100%)">
        <VStack align="stretch" spacing={3}>
          <HStack justify="space-between">
            <Heading size="lg" color="white">
              {resultData.title}
            </Heading>
            <Button
              leftIcon={<FiDownload />}
              colorScheme="whiteAlpha"
              variant="solid"
              onClick={handleDownloadMinutes}
              size="lg"
              px={12}
              py={8}
              fontSize="lg"
              fontWeight="bold"
              height="60px"
              _hover={{ transform: "scale(0.9)", boxShadow: "lg" }}
              transition="all 0.2s"
            >
              RAG Custom 회의록
            </Button>
          </HStack>
          <HStack fontSize="sm" color="whiteAlpha.900">
            <Text>{resultData.date}</Text>
            <Text>·</Text>
            <Text>AI 분석 리포트</Text>
          </HStack>
        </VStack>
      </Card>

      {/* 탭 메뉴 */}
      <Tabs index={tabIndex} onChange={setTabIndex} colorScheme="purple">
        <TabList mb={6} bg="white" p={2} borderRadius="12px">
          <Tab>
            <HStack>
              <FiFileText />
              <Text>회의록</Text>
            </HStack>
          </Tab>
          <Tab>
            <HStack>
              <FiTrendingUp />
              <Text>심층 분석</Text>
            </HStack>
          </Tab>
          <Tab>
            <HStack>
              <FiCheckCircle />
              <Text>자동화 승인</Text>
            </HStack>
          </Tab>
        </TabList>

        <TabPanels>
          {/* Tab 1: 회의록 */}
          <TabPanel p={0}>
            <VStack align="stretch" spacing={6}>
              <Card>
                <Heading size="md" mb={3}>
                  📝 회의 요약
                </Heading>
                {isLoading ? (
                  <VStack py={8}>
                    <Spinner size="xl" color="purple.500" />
                    <Text mt={4}>AI 분석 중...</Text>
                  </VStack>
                ) : (
                  <Text color="gray.700" lineHeight="1.8" whiteSpace="pre-line">
                    {realSummary || resultData.summary}
                  </Text>
                )}
              </Card>

              {/* 결정사항 */}
              <Card>
                <Heading size="md" mb={3}>
                  ✅ 주요 결정사항
                </Heading>
                <VStack align="stretch" spacing={2}>
                  {resultData.decisions.map((decision, i) => (
                    <HStack key={i} p={3} bg="blue.50" borderRadius="8px">
                      <Badge colorScheme="blue">{i + 1}</Badge>
                      <Text>{decision}</Text>
                    </HStack>
                  ))}
                </VStack>
              </Card>

              {/* 전체 녹음 */}
              <Card>
                <Heading size="md">💬 전체 녹음</Heading>
                <Box
                  bg="gray.50"
                  p={4}
                  borderRadius="8px"
                  fontSize="sm"
                  whiteSpace="pre-wrap"
                >
                  {transcript || resultData.transcript}
                </Box>
              </Card>
            </VStack>
          </TabPanel>

          {/* Tab 2: 심층 분석 */}
          <TabPanel p={0}>
            <VStack align="stretch" spacing={6}>
              <Card>
                <Heading size="md">📊 회의 분석</Heading>
                <Text>유형: {resultData.insights.meetingType}</Text>
                <Text>분위기: {resultData.insights.sentiment}</Text>
              </Card>
              {/* 리스크 분석 */}
              <Card>
                <Heading size="md" mb={3}>
                  ⚠️ 리스크 분석
                </Heading>
                <VStack align="stretch">
                  {resultData.insights.risks.map((risk, i) => (
                    <Box key={i} p={3} bg="red.50" borderRadius="8px">
                      <Text fontWeight="bold">{risk.level.toUpperCase()}</Text>
                      <Text>{risk.description}</Text>
                      {/* <Text fontWeight="bold">{(risk.level || 'MEDIUM').toUpperCase()}</Text>
                      <Text>{risk.description || (typeof risk === 'string' ? risk : '상세 내용 없음')}</Text> */}
                    </Box>
                  ))}
                </VStack>
              </Card>
            </VStack>
          </TabPanel>

          {/* Tab 3: 자동화 승인 */}
          <TabPanel p={0}>
            <VStack align="stretch" spacing={6}>
              {/* ▼▼▼ [디자인 복구] 팀원이 만든 차별화 포인트 강조 카드 ▼▼▼ */}
              <Card bg="linear-gradient(to right, #f3e8ff, #e9d5ff)">
                <HStack spacing={4} align="start">
                  <Box p={3} bg="white" borderRadius="12px" boxShadow="sm">
                    <Text fontSize="3xl">🚀</Text>
                  </Box>
                  <Box flex="1">
                    <Heading size="md" mb={2} color="purple.600">
                      이음의 차별화 포인트!
                    </Heading>
                    <Text color="gray.700" fontSize="sm" lineHeight="1.8">
                      Notion AI는 회의록을 저장하는 것으로 끝나지만,
                      <strong>
                        {" "}
                        이음은 회의 종료 후 자동으로 실행까지 연결
                      </strong>
                      합니다.
                      <br />
                      아래 항목을 체크하고 승인하면{" "}
                      <strong>수동 작업 15분을 3초로 단축</strong>할 수
                      있습니다.
                    </Text>
                  </Box>
                </HStack>
              </Card>

              {/* 
                  ▼▼▼ [기능 연결] ▼▼▼ 
                  1. approvalItems: 백엔드 데이터 연결
                  2. onSendEmail: 우리가 만든 메일 발송 함수 연결
              */}
              <ApprovalCenter
                approvalItems={resultData.approvalItems}
                onSendEmail={handleSendEmail}
              />

              {/* 🚨 아까 제가 추가했던 별도의 '승인 버튼' 박스는 제거했습니다. 
                  (ApprovalCenter 안에 이미 예쁜 버튼이 있으니까요!) */}
              <Box pt={6} pb={10}></Box>
            </VStack>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
}

export default Result;
