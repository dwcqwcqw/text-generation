import { NextRequest, NextResponse } from 'next/server';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

// 获取 R2 配置
function getR2Config() {
  const config = {
    accountId: process.env.R2_ACCOUNT_ID!,
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
    bucketName: 'text-generation',
    region: 'auto'
  };
  
  // 验证环境变量
  if (!config.accountId || !config.accessKeyId || !config.secretAccessKey) {
    throw new Error('R2 配置缺失，请设置环境变量：R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY');
  }
  
  return {
    ...config,
    endpoint: `https://${config.accountId}.r2.cloudflarestorage.com`
  };
}

// 创建 S3 客户端（R2 兼容 S3 API）
function createR2Client() {
  const config = getR2Config();
  return new S3Client({
    region: config.region,
    endpoint: config.endpoint,
    credentials: {
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey,
    },
  });
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    const fileName = formData.get('fileName') as string;
    
    if (!file || !fileName) {
      return NextResponse.json(
        { error: '缺少文件或文件名' },
        { status: 400 }
      );
    }

    console.log('📤 开始上传文件到 R2:', fileName, '大小:', file.size);

    // 获取配置和客户端
    const config = getR2Config();
    const r2Client = createR2Client();

    // 将文件转换为 Buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // 上传到 R2
    const uploadCommand = new PutObjectCommand({
      Bucket: config.bucketName,
      Key: fileName,
      Body: buffer,
      ContentType: file.type,
      ContentLength: buffer.length,
    });

    await r2Client.send(uploadCommand);

    // 返回公共 URL
    const publicUrl = `https://pub-f314a707297b4748936925bba8dd4962.r2.dev/${fileName}`;
    
    console.log('✅ 文件上传成功:', publicUrl);

    return NextResponse.json({
      success: true,
      url: publicUrl,
      fileName: fileName,
      size: file.size
    });

  } catch (error) {
    console.error('❌ R2 上传失败:', error);
    return NextResponse.json(
      { 
        error: error instanceof Error ? error.message : '上传失败',
        success: false 
      },
      { status: 500 }
    );
  }
} 