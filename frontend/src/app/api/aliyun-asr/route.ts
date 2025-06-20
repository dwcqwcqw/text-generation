import { NextRequest, NextResponse } from 'next/server';

// 阿里云 SDK 相关类型和函数的简化实现
class AcsClient {
  private accessKeyId: string;
  private accessKeySecret: string;
  private region: string;

  constructor(accessKeyId: string, accessKeySecret: string, region: string) {
    this.accessKeyId = accessKeyId;
    this.accessKeySecret = accessKeySecret;
    this.region = region;
  }

  async doActionWithException(request: any): Promise<string> {
    const { domain, version, action, method, queryParams, bodyParams } = request;
    
    // 构建请求URL
    const baseUrl = `https://${domain}`;
    const timestamp = new Date().toISOString().replace(/[:\-]|\.\d{3}/g, '');
    
    // 构建请求参数
    const params = new URLSearchParams({
      'Format': 'JSON',
      'Version': version,
      'Action': action,
      'SignatureMethod': 'HMAC-SHA1',
      'SignatureNonce': Math.random().toString(36).substring(2),
      'SignatureVersion': '1.0',
      'AccessKeyId': this.accessKeyId,
      'Timestamp': timestamp,
      ...queryParams
    });
    
    // 添加请求体参数
    if (bodyParams) {
      Object.entries(bodyParams).forEach(([key, value]) => {
        params.append(key, value as string);
      });
    }
    
    // 生成签名
    const signature = this.generateSignature(method, params);
    params.append('Signature', signature);
    
    // 发送请求
    const url = `${baseUrl}/?${params.toString()}`;
    const response = await fetch(url, {
      method: method,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.text();
  }

  private generateSignature(method: string, params: URLSearchParams): string {
    // 简化的阿里云签名算法
    const sortedParams = Array.from(params.entries()).sort();
    const queryString = sortedParams
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&');
    
    const stringToSign = `${method}&${encodeURIComponent('/')}&${encodeURIComponent(queryString)}`;
    const signingKey = `${this.accessKeySecret}&`;
    
    // 使用 HMAC-SHA1 生成签名
    const crypto = require('crypto');
    const signature = crypto
      .createHmac('sha1', signingKey)
      .update(stringToSign, 'utf8')
      .digest('base64');
    
    return signature;
  }
}

class CommonRequest {
  private domain: string = '';
  private version: string = '';
  private action: string = '';
  private method: string = 'POST';
  private queryParams: Record<string, string> = {};
  private bodyParams: Record<string, string> = {};

  setDomain(domain: string) {
    this.domain = domain;
  }

  setVersion(version: string) {
    this.version = version;
  }

  setActionName(action: string) {
    this.action = action;
  }

  setMethod(method: string) {
    this.method = method;
  }

  addQueryParam(key: string, value: string) {
    this.queryParams[key] = value;
  }

  addBodyParams(key: string, value: string) {
    this.bodyParams[key] = value;
  }

  getRequestData() {
    return {
      domain: this.domain,
      version: this.version,
      action: this.action,
      method: this.method,
      queryParams: this.queryParams,
      bodyParams: this.bodyParams
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, accessKeyId, accessKeySecret, appKey, fileLink, version, enableWords, taskId } = body;

    // 创建 ACS 客户端
    const client = new AcsClient(accessKeyId, accessKeySecret, 'cn-shanghai');

    if (action === 'submit') {
      // 提交录音文件识别任务
      const postRequest = new CommonRequest();
      postRequest.setDomain('nls-meta.cn-shanghai.aliyuncs.com');
      postRequest.setVersion('2019-02-28');
      postRequest.setActionName('SubmitTask');
      postRequest.setMethod('POST');

      const task = {
        appkey: appKey,
        file_link: fileLink,
        version: version,
        enable_words: enableWords
      };

      postRequest.addBodyParams('Task', JSON.stringify(task));

      const response = await client.doActionWithException(postRequest.getRequestData());
      const result = JSON.parse(response);
      
      return NextResponse.json(result);

    } else if (action === 'query') {
      // 查询识别结果
      const getRequest = new CommonRequest();
      getRequest.setDomain('nls-meta.cn-shanghai.aliyuncs.com');
      getRequest.setVersion('2019-02-28');
      getRequest.setActionName('GetTaskResult');
      getRequest.setMethod('GET');
      getRequest.addQueryParam('TaskId', taskId);

      const response = await client.doActionWithException(getRequest.getRequestData());
      const result = JSON.parse(response);
      
      return NextResponse.json(result);

    } else {
      return NextResponse.json(
        { error: '不支持的操作类型' },
        { status: 400 }
      );
    }

  } catch (error) {
    console.error('阿里云 ASR API 错误:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '服务器内部错误' },
      { status: 500 }
    );
  }
} 