import React, { useState, useEffect } from "react";
import {
  Box,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  Icon,
  List,
  ListItem,
  Badge,
  useToast,
  Progress,
  SimpleGrid,
} from "@chakra-ui/react";
import { FiUpload, FiFile, FiTrash2, FiCheckCircle } from "react-icons/fi";
import Card from "../components/Card";

const API_URL = import.meta.env.VITE_API_URL;

const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

function Upload() {
  // 각 섹션별 파일 상태 관리
  const [ieumFiles, setIeumFiles] = useState([]);
  const [customFiles, setCustomFiles] = useState([]);
  const [externalFiles, setExternalFiles] = useState([]);
  const [isUploading, setIsUploading] = useState({
    ieum: false,
    custom: false,
    external: false,
  });
  const [uploadProgress, setUploadProgress] = useState({
    ieum: 0,
    custom: 0,
    external: 0,
  });
  const toast = useToast();

  // 컴포넌트 마운트 시 파일 목록 불러오기
  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await fetch(`${API_URL}/files`);
      if (!response.ok) throw new Error("파일 목록 로드 실패");
      
      const data = await response.json();
      
      // 백엔드 카테고리(history/style/reference)를 프론트엔드 섹션(ieum/custom/external)으로 매핑
      const ieum = [];
      const custom = [];
      const external = [];

      data.files.forEach(file => {
        // UI에 보여줄 객체 형태로 변환
        const fileObj = {
          id: file.id,
          name: file.name,
          size: file.size,
          type: file.name.split(".").pop().toUpperCase(),
          uploadDate: file.uploadDate,
          status: "completed"
        };

        if (file.category === "history") ieum.push(fileObj);
        else if (file.category === "style") custom.push(fileObj);
        else if (file.category === "reference") external.push(fileObj);
      });

      setIeumFiles(ieum);
      setCustomFiles(custom);
      setExternalFiles(external);

    } catch (error) {
      console.error("Fetch Error:", error);
      toast({
        title: "동기화 실패",
        description: "서버에서 파일 목록을 가져오지 못했습니다.",
        status: "error"
      });
    }
  };

  // 파일 크기 제한 (100MB)
  const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB in bytes

  // 파일 업로드 핸들러 (섹션별 + 용량 검증)
  const handleFileSelect = async (event, section) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    // 파일 크기 검증
    const validFiles = [];
    const invalidFiles = [];

    files.forEach((file) => {
      if (file.size > MAX_FILE_SIZE) {
        invalidFiles.push({
          name: file.name,
          size: formatBytes(file.size),
        });
      } else {
        validFiles.push(file);
      }
    });

    // 용량 초과 파일이 있는 경우 경고
    if (invalidFiles.length > 0) {
      const invalidFilesList = invalidFiles
        .map((f) => `• ${f.name} (${f.size})`)
        .join("\n");

      toast({
        title: "파일 크기 초과",
        description: `다음 파일은 100MB를 초과하여 업로드할 수 없습니다:\n\n${invalidFilesList}`,
        status: "error",
        duration: 6000,
        isClosable: true,
      });

      // 초과 파일만 있고 정상 파일이 없으면 종료
      if (validFiles.length === 0) {
        event.target.value = ""; // input 초기화
        return;
      }

      // 일부 파일만 초과한 경우 안내
      toast({
        title: "📋 일부 파일만 업로드됩니다",
        description: `${validFiles.length}개 파일은 정상적으로 업로드됩니다.`,
        status: "info",
        duration: 3000,
        isClosable: true,
      });
    }

    // 정상 파일만 업로드 진행
    if (validFiles.length > 0) {
      setIsUploading((prev) => ({ ...prev, [section]: true }));
      setUploadProgress((prev) => ({ ...prev, [section]: 0 }));

      for (const file of validFiles) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("category", section); // ieum, custom, external

        try {
          const response = await fetch(`${API_URL}/upload`, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) throw new Error("Upload failed");

          // 업로드 성공 시 상태 업데이트
          const newFile = {
            id: Date.now(),
            name: file.name,
            size: formatBytes(file.size),
            type: file.name.split(".").pop().toUpperCase(),
            uploadDate: new Date().toISOString().split("T")[0],
            status: "completed",
          };

          // 상태(State) 업데이트 로직
          if (section === "ieum") setIeumFiles(prev => [...prev, newFile]);
          else if (section === "custom") setCustomFiles(prev => [...prev, newFile]);
          else if (section === "external") setExternalFiles(prev => [...prev, newFile]);

        } catch (error) {
          console.error("Error:", error);
          toast({
            title: "업로드 실패",
            description: `${file.name} 업로드 중 오류가 발생했습니다.`,
            status: "error",
          });
        }
      }

      // 로딩 종료
      setIsUploading((prev) => ({ ...prev, [section]: false }));
      setUploadProgress((prev) => ({ ...prev, [section]: 100 }));
      
      toast({
        title: "✅ 처리 완료",
        description: `${validFiles.length}개 파일이 RAG 시스템에 등록되었습니다.`,
        status: "success",
      });
      
      event.target.value = "";
    }
  };

  // 파일 삭제 핸들러 (섹션별)
  const handleDelete = async (id, section, fileName) => {
    // API 호출: 백엔드에 삭제 요청
    try {
      const categoryMap = {
        "ieum": "history",
        "custom": "style",
        "external": "reference"
      };
      const backendCategory = categoryMap[section] || "reference";

      const response = await fetch(`${API_URL}/delete`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: fileName, // 예: meeting_log.docx
          category: backendCategory
        }),
      });

      if (!response.ok) throw new Error("삭제 실패");

      // UI 상태 업데이트
      if (section === "ieum") {
        setIeumFiles((prev) => prev.filter((file) => file.id !== id));
      } else if (section === "custom") {
        setCustomFiles((prev) => prev.filter((file) => file.id !== id));
      } else if (section === "external") {
        setExternalFiles((prev) => prev.filter((file) => file.id !== id));
      }

      toast({
        title: "파일 삭제 완료",
        description: "서버 및 RAG DB에서 영구적으로 삭제되었습니다.",
        status: "info",
        duration: 2000,
      });

    } catch (error) {
      console.error("Delete Error:", error);
      toast({
        title: "삭제 실패",
        description: "서버 통신 중 오류가 발생했습니다.",
        status: "error",
      });
    }
  };

  // 업로드 섹션 컴포넌트
  const UploadSection = ({
    title,
    description,
    bgGradient,
    fileList,
    section,
    acceptedFormats,
  }) => {
    // 섹션별 지원 형식 텍스트 결정
    const getFormatText = (sec) => {
      switch (sec) {
        case "custom":
          return "DOCX 전용 | 최대 100MB";
        case "external":
          return "PDF, DOCX, TXT | 최대 100MB";
        default:
          return "PDF, DOCX | 최대 100MB";
      }
    };

    return (
      <Card p={4} flex="1" minH="400px" display="flex" flexDirection="column">
        {/* 업로드 영역 */}
        <Box bg={bgGradient} p={6} borderRadius="12px" mb={4} textAlign="center">
          <VStack spacing={3}>
            <Icon as={FiUpload} boxSize={10} color="white" />
            <Heading size="sm" color="white">
              {title}
            </Heading>
            <Text color="whiteAlpha.900" fontSize="xs" textAlign="center">
              {description}
            </Text>

            <Button
              as="label"
              htmlFor={`file-upload-${section}`}
              size="sm"
              bg="white"
              color="primary.500"
              leftIcon={<FiUpload />}
              cursor="pointer"
              _hover={{ transform: "scale(1.05)" }}
              transition="all 0.2s"
              isDisabled={isUploading[section]}
            >
              파일 선택
            </Button>
            <input
              id={`file-upload-${section}`}
              type="file"
              accept={acceptedFormats}
              multiple
              style={{ display: "none" }}
              onChange={(e) => handleFileSelect(e, section)}
            />

            <Text fontSize="xs" color="whiteAlpha.800">
              {getFormatText(section)}
            </Text>
          </VStack>
        </Box>

        {/* 업로드 진행률 */}
        {isUploading[section] && (
          <Box mb={4} p={3} bg="gray.50" borderRadius="8px">
            <VStack spacing={2}>
              <HStack w="full" justify="space-between">
                <Text fontSize="sm" fontWeight="bold">
                  업로드 중...
                </Text>
                <Text fontSize="sm" color="gray.600">
                  {uploadProgress[section]}%
                </Text>
              </HStack>
              <Progress
                value={uploadProgress[section]}
                size="sm"
                colorScheme="purple"
                w="full"
                borderRadius="full"
                hasStripe
                isAnimated
              />
            </VStack>
          </Box>
        )}

        {/* 업로드된 파일 목록 */}
        <Box flex="1">
          <HStack justify="space-between" mb={3}>
            <Heading size="xs">업로드된 파일</Heading>
            <Badge colorScheme="purple" fontSize="xs">
              {fileList.length}개
            </Badge>
          </HStack>

          {fileList.length === 0 ? (
            <Box
              textAlign="center"
              py={6}
              color="gray.500"
              bg="gray.50"
              borderRadius="8px"
            >
              <Text fontSize="sm">업로드된 파일이 없습니다</Text>
            </Box>
          ) : (
            <Box maxH="300px" overflowY="auto" pr={2}>
              <List spacing={2}>
                {fileList.map((file) => (
                  <ListItem key={file.id}>
                    <HStack
                      p={3}
                      bg="gray.50"
                      borderRadius="8px"
                      justify="space-between"
                      _hover={{ bg: "gray.100" }}
                      transition="all 0.2s"
                    >
                      <HStack spacing={2} flex="1" minW="0">
                        <Icon
                          as={FiFile}
                          boxSize={4}
                          color="primary.500"
                          flexShrink="0"
                        />
                        <VStack align="start" spacing={0} flex="1" minW="0">
                          <Text
                            fontSize="xs"
                            fontWeight="bold"
                            noOfLines={1}
                            w="full"
                          >
                            {file.name}
                          </Text>
                          <HStack fontSize="xs" color="gray.600">
                            <Badge colorScheme="purple" fontSize="xs">
                              {file.type}
                            </Badge>
                            <Text fontSize="xs">{file.size}</Text>
                          </HStack>
                        </VStack>
                        {file.status === "completed" && (
                          <Icon
                            as={FiCheckCircle}
                            color="green.500"
                            boxSize={4}
                            flexShrink="0"
                          />
                        )}
                      </HStack>

                      <Button
                        size="xs"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => handleDelete(file.id, section, file.name)}
                        flexShrink="0"
                      >
                        삭제
                      </Button>
                    </HStack>
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </Box>
      </Card>
    )
  };

  return (
    <Box>
      <Heading size="xl" mb={6}>
        📤 RAG 데이터 업로드
      </Heading>

      {/* 3개 업로드 섹션 (가로 분할) */}
      <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={4} mb={6}>
        <UploadSection
          title="이음 AI 회의록"
          description="이음에서 자동 생성된 회의록을 업로드하세요"
          bgGradient="linear-gradient(135deg, #4811BF 0%, #8C5CF2 100%)"
          fileList={ieumFiles}
          section="ieum"
          acceptedFormats=".pdf,.docx"
        />

        <UploadSection
          title="Custom 회의록 양식"
          description="회사 양식에 맞춘 커스텀 템플릿을 업로드하세요"
          bgGradient="linear-gradient(135deg, #8C5CF2 0%, #B794F6 100%)"
          fileList={customFiles}
          section="custom"
          acceptedFormats=".docx"
        />

        <UploadSection
          title="외부 자료"
          description="회의 인사이트를 도출할 자료를 업로드하세요"
          bgGradient="linear-gradient(135deg, #09A603 0%, #38B2AC 100%)"
          fileList={externalFiles}
          section="external"
          acceptedFormats=".pdf,.docx,.txt"
        />
      </SimpleGrid>

      {/* 안내 사항 */}
      <Card bg="blue.50">
        <VStack align="start" spacing={2}>
          <Heading size="sm" color="blue.700">
            💡 RAG 시스템 안내
          </Heading>
          <Text fontSize="sm" color="blue.700" lineHeight="1.8">
            • <strong>이음 AI 회의록</strong>: 과거 회의 내용 기록 파일 (PDF, DOCX | 최대 100MB)
            <br />• <strong>Custom 회의록 양식</strong>: 결과물 생성에 사용될 서식 템플릿 (DOCX 전용 | 최대 100MB)
            <br />• <strong>외부 자료</strong>: 마케팅 자료, 리서치 문서 등 회의 인사이트 도출에 필요한 자료 (PDF, DOCX, TXT | 최대 100MB)
            <br />• <strong>파일 크기 제한</strong>: 각 파일은 최대 100MB까지 업로드 가능합니다.
            <br />• <strong>주의</strong>: 암호가 걸린 문서나 스캔된 이미지형 PDF는 텍스트 추출이 불가합니다.
            <br />• 업로드된 파일은 벡터 데이터베이스에 저장되며, 회의 중 AI가 자동으로 관련 내용을 찾아드립니다.
            <br />• 데이터베이스는 Microsoft Azure의 엔터프라이즈급 보안으로 철저히 보호됩니다.
          </Text>
        </VStack>
      </Card>
    </Box>
  );
}

export default Upload;
