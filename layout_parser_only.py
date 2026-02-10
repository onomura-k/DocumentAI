"""
Layout Parser単体テスト - テキスト・構造解析確認用
Document AI Layout Parserのみを使用してテキスト抽出と構造解析を検証
"""

import os
import json
import io
from PIL import Image
from google.cloud import documentai_v1beta3 as documentai

class LayoutParserTest:
    """Layout Parser単体テスト"""
    
    def __init__(self):
        self.config = {
            "project_id": "gen-lang-client-0849825641",
            "documentai_location": "us",
            "layout_parser_processor_id": "6af87434352688a1",
            "pdf_path": "sample.pdf"
        }
        
        # Document AI クライアント初期化
        self.client = documentai.DocumentProcessorServiceClient()
        
        # プロセッサ名の正式な形式で構築
        self.processor_name = self.client.processor_path(
            self.config['project_id'],
            self.config['documentai_location'], 
            self.config['layout_parser_processor_id']
        )
        
    def get_process_options(self):
        """公式リファレンス準拠の正しいLayoutConfig設定"""
        from google.cloud import documentai_v1beta3 as documentai
        
        return documentai.ProcessOptions(
            layout_config=documentai.ProcessOptions.LayoutConfig(
                # 1. チャンキング設定
                chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                    chunk_size=500,
                    include_ancestor_headings=True
                ),
                
                # 2. 🎯 公式リファレンス準拠の座標・画像取得設定
                return_images=True,              # 📋 公式: 画像データを返却
                return_bounding_boxes=True,      # 📋 公式: 座標データ(バウンディングボックス)を返却
                
                # 3. 解析・抽出の有効化
                enable_llm_layout_parsing=True,  # LLMによる解析
                enable_image_extraction=True,   # 画像抽出
                enable_image_annotation=True,   # 画像注釈（座標強化）
                enable_table_annotation=True    # 表の解析
            )
        )
        
    def deep_investigate_bounding_boxes(self, document):
        """Layout Parser特有のバウンディングボックス格納場所を徹底調査"""
        
        print(f"\n🔬 Layout Parser座標データ徹底調査:")
        print("=" * 60)
        
        coordinates_found = []
        
        # 1. 📋 document_layout.blocks のより深い調査
        if hasattr(document, 'document_layout') and document.document_layout and document.document_layout.blocks:
            print(f"\n1️⃣ document_layout.blocks 深層調査:")
            
            for block_idx, block in enumerate(document.document_layout.blocks):
                print(f"\n   ブロック{block_idx+1} 全属性スキャン:")
                
                # 全属性を徹底的にスキャン
                all_attrs = dir(block)
                relevant_attrs = [attr for attr in all_attrs if not attr.startswith('_')]
                
                print(f"   利用可能な全属性: {relevant_attrs}")
                
                # 各属性を詳細チェック
                for attr in relevant_attrs:
                    try:
                        attr_value = getattr(block, attr)
                        if attr_value is not None:
                            # 座標関連の属性を特定
                            if 'box' in attr.lower() or 'bound' in attr.lower() or 'coord' in attr.lower() or 'vertex' in attr.lower():
                                print(f"   🎯 座標候補属性発見: {attr} = {type(attr_value)}")
                                
                                # BoundingPolyの詳細調査
                                if 'BoundingPoly' in str(type(attr_value)):
                                    print(f"      BoundingPoly詳細調査:")
                                    poly_attrs = dir(attr_value)
                                    poly_relevant = [pa for pa in poly_attrs if not pa.startswith('_')]
                                    print(f"      利用可能属性: {poly_relevant}")
                                    
                                    for poly_attr in poly_relevant:
                                        try:
                                            poly_value = getattr(attr_value, poly_attr)
                                            if poly_value is not None:
                                                print(f"      {poly_attr}: {type(poly_value)} = {poly_value}")
                                                
                                                # verticesの詳細調査
                                                if 'vertices' in poly_attr and hasattr(poly_value, '__len__'):
                                                    print(f"         vertices長さ: {len(poly_value)}")
                                                    if len(poly_value) > 0:
                                                        for i, vertex in enumerate(poly_value[:4]):  # 最初の4個のみ
                                                            if hasattr(vertex, 'x') and hasattr(vertex, 'y'):
                                                                print(f"         vertex[{i}]: ({vertex.x}, {vertex.y})")
                                            else:
                                                print(f"      {poly_attr}: None")
                                        except Exception as e:
                                            print(f"      {poly_attr}調査エラー: {e}")
                                
                                # 属性の詳細調査
                                if hasattr(attr_value, '__iter__') and not isinstance(attr_value, (str, bytes)):
                                    try:
                                        items = list(attr_value)
                                        print(f"      反復可能オブジェクト: {len(items)}個の要素")
                                        if items:
                                            print(f"      最初の要素型: {type(items[0])}")
                                    except Exception as e:
                                        print(f"      反復調査エラー: {e}")
                                
                                # 座標データ抽出を試行
                                coords = self._extract_coordinates_from_object(attr_value, f"block_{block_idx+1}.{attr}")
                                if coords:
                                    coordinates_found.extend(coords)
                                    print(f"      ✅ 座標データ取得成功: {len(coords)}セット")
                            
                            # 特定属性の詳細調査
                            elif attr in ['bounding_box', 'page_span', 'text_block', 'image_block']:
                                print(f"   📍 重要属性詳細: {attr} = {type(attr_value)}")
                                
                                # さらに深い階層を調査
                                if hasattr(attr_value, '__dict__') or hasattr(attr_value, '__slots__'):
                                    sub_attrs = dir(attr_value)
                                    coord_sub_attrs = [sub for sub in sub_attrs if not sub.startswith('_')]
                                    print(f"      サブ属性: {coord_sub_attrs[:10]}...")
                                    
                                    # サブ属性から座標検索
                                    for sub_attr in coord_sub_attrs:
                                        if 'vertex' in sub_attr.lower() or 'bound' in sub_attr.lower():
                                            try:
                                                sub_value = getattr(attr_value, sub_attr)
                                                if sub_value:
                                                    print(f"      🎯 サブ座標候補: {attr}.{sub_attr} = {type(sub_value)}")
                                                    coords = self._extract_coordinates_from_object(sub_value, f"block_{block_idx+1}.{attr}.{sub_attr}")
                                                    if coords:
                                                        coordinates_found.extend(coords)
                                                        print(f"      ✅ サブ座標取得成功: {len(coords)}セット")
                                                else:
                                                    print(f"      {attr}.{sub_attr}: 空またはNone")
                                            except Exception as e:
                                                print(f"      サブ属性エラー: {e}")
                    
                    except Exception as e:
                        print(f"   属性{attr}調査エラー: {e}")
        
        # 2. 📄 pages 構造の再調査（Layout Parser特有の場所を探す）
        if hasattr(document, 'pages') and document.pages:
            print(f"\n2️⃣ document.pages Layout Parser特化調査:")
            
            for page_idx, page in enumerate(document.pages):
                print(f"\n   ページ{page_idx+1} 全属性調査:")
                
                page_attrs = dir(page)
                page_relevant = [attr for attr in page_attrs if not attr.startswith('_')]
                print(f"   ページ属性: {page_relevant}")
                
                # Layout Parser特有の属性を探す
                for attr in page_relevant:
                    try:
                        attr_value = getattr(page, attr)
                        if attr_value and hasattr(attr_value, '__len__'):
                            if 'layout' in attr.lower() or 'block' in attr.lower() or 'element' in attr.lower():
                                print(f"   🎯 Layout関連属性: {attr} = {type(attr_value)}, 長さ: {len(attr_value) if hasattr(attr_value, '__len__') else 'N/A'}")
                                
                                # Layout関連属性の詳細調査
                                if hasattr(attr_value, '__iter__') and len(attr_value) > 0:
                                    first_item = attr_value[0] if attr_value else None
                                    if first_item:
                                        item_attrs = dir(first_item)
                                        coord_attrs = [ia for ia in item_attrs if not ia.startswith('_') and ('bound' in ia.lower() or 'coord' in ia.lower() or 'vertex' in ia.lower())]
                                        if coord_attrs:
                                            print(f"      座標関連サブ属性発見: {coord_attrs}")
                                            
                                            # 実際の座標抽出
                                            for coord_attr in coord_attrs:
                                                try:
                                                    coord_value = getattr(first_item, coord_attr)
                                                    coords = self._extract_coordinates_from_object(coord_value, f"page_{page_idx+1}.{attr}[0].{coord_attr}")
                                                    if coords:
                                                        coordinates_found.extend(coords)
                                                        print(f"      ✅ 座標取得成功: {coord_attr} から {len(coords)}セット")
                                                except Exception as e:
                                                    print(f"      座標抽出エラー: {e}")
                    except Exception as e:
                        print(f"   ページ属性{attr}エラー: {e}")
        
        # 3. 🔍 その他の可能な座標格納場所
        print(f"\n3️⃣ その他の座標格納場所調査:")
        
        # document直下の他の属性をチェック
        doc_attrs = dir(document)
        coord_candidate_attrs = [attr for attr in doc_attrs if not attr.startswith('_') and 
                               ('layout' in attr.lower() or 'bound' in attr.lower() or 'coord' in attr.lower() or 'element' in attr.lower())]
        
        print(f"   座標候補属性: {coord_candidate_attrs}")
        
        for attr in coord_candidate_attrs:
            try:
                attr_value = getattr(document, attr)
                if attr_value:
                    print(f"   🔍 {attr}: {type(attr_value)}")
                    coords = self._extract_coordinates_from_object(attr_value, f"document.{attr}")
                    if coords:
                        coordinates_found.extend(coords)
                        print(f"   ✅ {attr}から座標取得: {len(coords)}セット")
            except Exception as e:
                print(f"   {attr}調査エラー: {e}")
        
        # 結果サマリー
        print(f"\n📊 Layout Parser座標調査結果:")
        print(f"   発見された座標セット: {len(coordinates_found)}個")
        
        if coordinates_found:
            for i, coord_set in enumerate(coordinates_found):
                print(f"   座標セット{i+1}: {coord_set['source']} - {len(coord_set['coordinates'])}個の点")
                if coord_set['coordinates']:
                    first_coord = coord_set['coordinates'][0]
                    last_coord = coord_set['coordinates'][-1]
                    print(f"      範囲: ({first_coord['x']:.3f}, {first_coord['y']:.3f}) → ({last_coord['x']:.3f}, {last_coord['y']:.3f})")
        else:
            print("   ❌ 座標データは発見されませんでした")
        
        return coordinates_found
    
    def _extract_coordinates_from_object(self, obj, source_path):
        """オブジェクトから座標データを抽出する汎用メソッド"""
        coordinates = []
        
        try:
            # 1. 直接的な頂点リスト
            if hasattr(obj, 'normalized_vertices') or hasattr(obj, 'vertices'):
                for vertex_attr in ['normalized_vertices', 'vertices']:
                    if hasattr(obj, vertex_attr):
                        vertices = getattr(obj, vertex_attr)
                        if vertices and len(vertices) >= 4:
                            coord_list = []
                            for vertex in vertices:
                                coord_list.append({
                                    "x": getattr(vertex, 'x', 0),
                                    "y": getattr(vertex, 'y', 0)
                                })
                            
                            coordinates.append({
                                "source": f"{source_path}.{vertex_attr}",
                                "coordinates": coord_list
                            })
            
            # 2. バウンディングボックスオブジェクト
            elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
                # リストやタプルの場合、各要素をチェック
                try:
                    for i, item in enumerate(obj):
                        if hasattr(item, 'normalized_vertices') or hasattr(item, 'vertices'):
                            item_coords = self._extract_coordinates_from_object(item, f"{source_path}[{i}]")
                            coordinates.extend(item_coords)
                except Exception:
                    pass
            
            # 3. 座標らしき数値属性の組み合わせ
            elif hasattr(obj, 'x') and hasattr(obj, 'y'):
                coordinates.append({
                    "source": source_path,
                    "coordinates": [{
                        "x": getattr(obj, 'x', 0),
                        "y": getattr(obj, 'y', 0)
                    }]
                })
            
        except Exception as e:
            print(f"   座標抽出エラー ({source_path}): {e}")
        
        return coordinates
        
    def analyze_layout_parser_result(self):
        """Layout Parser結果の詳細解析"""
        
        print("🔍 Layout Parser単体テスト開始")
        print("=" * 50)
        
        try:
            # PDFファイル読み込み
            with open(self.config["pdf_path"], "rb") as f:
                pdf_content = f.read()
            
            print(f"📁 PDF読み込み: {self.config['pdf_path']} ({len(pdf_content)} bytes)")
            
            # プロセッサ情報を事前確認
            self._check_processor_info()
            
            # Layout Parserプロセッサー設定
            processor_name = f"projects/{self.config['project_id']}/locations/{self.config['documentai_location']}/processors/{self.config['layout_parser_processor_id']}"
            
            # Document AI リクエスト（高度オプション対応版）
            raw_document = documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
            
            # 1. v1beta3 最新のレイアウト設定を取得
            process_options = self.get_process_options()
            
            # 2. リクエストに process_options を含める
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
                process_options=process_options  # ← ここが重要！
            )
            
            print("🔧 v1beta3 公式リファレンス準拠設定:")
            print(f"   プロセッサ: Layout Parser (座標・画像取得特化)")
            print(f"   ✅ チャンキング設定: chunk_size=500, include_ancestor_headings=True")
            print(f"   🎯 returnImages: True (LayoutConfig内 - 公式準拠)")
            print(f"   🎯 returnBoundingBoxes: True (LayoutConfig内 - 公式準拠)")
            print(f"   ✅ enableImageAnnotation: True")
            print(f"   ✅ enableImageExtraction: True")
            print(f"   ✅ enableTableAnnotation: True")
            print(f"   ✅ enableLlmLayoutParsing: True (最新Geminiベース)")
            
            print("🚀 Layout Parser実行中...")
            result = self.client.process_document(request=request)
            document = result.document
            
            print("✅ Layout Parser処理完了\n")
            
            # 詳細解析開始
            self._analyze_document_structure(document)
            self._extract_all_text_methods(document) 
            
            # 🆕 個別画像切り抜き処理を追加
            print("\n" + "="*50)
            print("🖼️ 個別画像切り抜き処理")
            print("="*50)
            
            # 🔬 詳細調査を最初に実行
            image_block_findings = self.deep_investigate_image_blocks(document)
            
            # � Layout Parser特有の座標データ徹底調査
            layout_coordinates = self.deep_investigate_bounding_boxes(document)
            
            # �🎯 重要: document.pages[].blocks の座標調査を追加
            page_blocks_findings = self.investigate_pages_blocks_coordinates(document)
            
            extracted_figures = []
            if hasattr(document, 'pages') and document.pages:
                for page_idx in range(len(document.pages)):
                    # 🆕 pages.blocks座標を使った切り抜きを優先実行
                    page_figures = self.extract_from_pages_blocks(document, page_idx, page_blocks_findings)
                    extracted_figures.extend(page_figures)
                    
                    # 従来の方法もバックアップとして実行
                    additional_figures = self.extract_individual_images(document, page_idx)
                    extracted_figures.extend(additional_figures)
            else:
                print("❌ document.pagesが存在しないため、個別画像切り抜きはスキップされます")
            
            self._save_detailed_results(document, extracted_figures, image_block_findings, layout_coordinates)
            
        except Exception as e:
            print(f"❌ Layout Parserエラー: {e}")
    
    def _analyze_correct_field_references(self, document):
        """適切なフィールド参照による詳細調査 - page_anchor を使った正しい座標取得"""
        
        print("🎯 適切なフィールド参照解析:")
        print("-" * 50)
        
        analysis_results = {
            "pages_data": [],
            "document_layout_analysis": {},
            "summary": {
                "total_coordinates": 0,
                "total_visual_elements": 0,
                "total_images": 0,
                "coordinate_extraction_success": False,
                "visual_elements_extraction_success": False,
                "image_extraction_success": False
            }
        }
        
        # 1. document.document_layout解析（構造データ）
        print(f"📋 document.document_layout解析:")
        layout_blocks_with_coordinates = []
        
        if hasattr(document, 'document_layout') and document.document_layout:
            if hasattr(document.document_layout, 'blocks') and document.document_layout.blocks:
                print(f"   document_layout.blocks: {len(document.document_layout.blocks)}個")
                
                for block_idx, block in enumerate(document.document_layout.blocks):
                    print(f"\n   === ブロック{block_idx+1} 詳細解析 ===")
                    
                    block_info = {
                        "block_id": block_idx + 1,
                        "text": "",
                        "coordinates": [],
                        "page_anchor_info": {},
                        "layout_info": {}
                    }
                    
                    # テキスト取得
                    if hasattr(block, 'text_block') and block.text_block:
                        block_info["text"] = block.text_block.text
                        print(f"     テキスト: '{block_info['text'][:50]}...'")
                    
                    # ブロックの全属性を調査
                    block_attrs = dir(block)
                    relevant_block_attrs = [attr for attr in block_attrs if not attr.startswith('_')]
                    print(f"     ブロック属性: {relevant_block_attrs}")
                    
                    # 🎯 bounding_box を詳細調査（これが座標の格納場所！）
                    if hasattr(block, 'bounding_box') and block.bounding_box:
                        bounding_box = block.bounding_box
                        print(f"     ✅ bounding_box: 存在! (これが座標データ)")
                        
                        # bounding_boxの属性を調査
                        bbox_attrs = dir(bounding_box)
                        relevant_bbox_attrs = [attr for attr in bbox_attrs if not attr.startswith('_')]
                        print(f"     bounding_box属性: {relevant_bbox_attrs}")
                        
                        # 各bounding_box属性の内容を確認
                        bbox_data = {}
                        coordinates_extracted = []
                        
                        for attr in relevant_bbox_attrs:
                            try:
                                value = getattr(bounding_box, attr)
                                bbox_data[attr] = str(value)[:100] if value is not None else None
                                print(f"       bounding_box.{attr}: {type(value)} = {str(value)[:200]}...")
                                
                                # 座標データの取得を試行
                                if attr in ['normalized_vertices', 'vertices'] and value:
                                    print(f"       🎯 {attr}から座標抽出を試行...")
                                    try:
                                        vertices = []
                                        for vertex in value:
                                            vertices.append({
                                                "x": getattr(vertex, 'x', 0),
                                                "y": getattr(vertex, 'y', 0)
                                            })
                                        
                                        coordinates_extracted.append({
                                            "source": f"bounding_box.{attr}",
                                            "coordinates": vertices,
                                            "count": len(vertices)
                                        })
                                        print(f"       ✅ 座標取得成功: {len(vertices)}個の頂点")
                                    except Exception as e:
                                        print(f"       ❌ 座標抽出エラー: {e}")
                                        
                            except Exception as e:
                                print(f"       bounding_box.{attr}: エラー - {e}")
                        
                        if coordinates_extracted:
                            block_info["coordinates"] = coordinates_extracted
                            analysis_results["summary"]["total_coordinates"] += sum(c["count"] for c in coordinates_extracted)
                            print(f"     🎯 ブロック{block_idx+1} 座標取得成功: {len(coordinates_extracted)}セット")
                        
                        block_info["bounding_box_info"] = {
                            "has_bounding_box": True,
                            "attributes": relevant_bbox_attrs,
                            "data": bbox_data
                        }
                    else:
                        print(f"     ❌ bounding_box: なし")
                        block_info["bounding_box_info"] = {"has_bounding_box": False}
                    
                    # layout情報も調査（後方互換性のため）
                    if hasattr(block, 'layout') and block.layout:
                        layout = block.layout
                        print(f"     layout: 存在（追加確認）")
                        
                        # layoutの全属性を調査
                        layout_attrs = dir(layout)
                        relevant_layout_attrs = [attr for attr in layout_attrs if not attr.startswith('_')]
                        print(f"     layout属性: {relevant_layout_attrs}")
                        
                        block_info["layout_info"]["attributes"] = relevant_layout_attrs
                        
                        # page_anchorを特に詳しく調査
                        if hasattr(layout, 'page_anchor') and layout.page_anchor:
                            page_anchor = layout.page_anchor
                            print(f"     ✅ page_anchor: 存在!")
                            
                            # page_anchorの属性を調査
                            anchor_attrs = dir(page_anchor)
                            relevant_anchor_attrs = [attr for attr in anchor_attrs if not attr.startswith('_')]
                            print(f"     page_anchor属性: {relevant_anchor_attrs}")
                            
                            block_info["page_anchor_info"] = {
                                "has_page_anchor": True,
                                "attributes": relevant_anchor_attrs
                            }
                        else:
                            print(f"     page_anchor: なし")
                    else:
                        print(f"     layout: なし")
                    
                    layout_blocks_with_coordinates.append(block_info)
            else:
                print(f"   ❌ document_layout.blocksが存在しません")
        
        analysis_results["document_layout_analysis"] = {
            "blocks_count": len(layout_blocks_with_coordinates),
            "blocks_with_coordinates": layout_blocks_with_coordinates
        }
        
        # 2. document.pages解析（生データ）
        if hasattr(document, 'pages') and document.pages:
            print(f"\n📄 document.pages解析: {len(document.pages)}ページ")
            
            for page_idx, page in enumerate(document.pages):
                print(f"\n  ページ {page_idx + 1}:")
                
                page_data = {
                    "page": page_idx + 1,
                    "coordinates": [],
                    "visual_elements": [],
                    "image_data": {},
                    "raw_elements_count": {}
                }
                
                # 生データ要素をカウント
                for element_type in ['blocks', 'paragraphs', 'lines', 'tokens']:
                    if hasattr(page, element_type):
                        elements = getattr(page, element_type)
                        count = len(elements) if elements else 0
                        page_data["raw_elements_count"][element_type] = count
                        print(f"    {element_type}: {count}個")
                
                # 画像データの取得
                image_found = self._extract_page_image_data(page, page_data)
                if image_found:
                    analysis_results["summary"]["total_images"] += 1
                
                # ビジュアル要素の取得
                visual_elements_found = self._extract_page_visual_elements(page, page_data)
                analysis_results["summary"]["total_visual_elements"] += len(page_data["visual_elements"])
                
                analysis_results["pages_data"].append(page_data)
        
        # 成功フラグ更新
        analysis_results["summary"]["coordinate_extraction_success"] = analysis_results["summary"]["total_coordinates"] > 0
        analysis_results["summary"]["visual_elements_extraction_success"] = analysis_results["summary"]["total_visual_elements"] > 0
        analysis_results["summary"]["image_extraction_success"] = analysis_results["summary"]["total_images"] > 0
        
        # 結果サマリー表示
        print(f"\n📊 フィールド参照解析結果:")
        print(f"   座標データ: {analysis_results['summary']['total_coordinates']}個 ({'✅ 成功' if analysis_results['summary']['coordinate_extraction_success'] else '❌ 失敗'})")
        print(f"   画像データ: {analysis_results['summary']['total_images']}個 ({'✅ 成功' if analysis_results['summary']['image_extraction_success'] else '❌ 失敗'})")
        print(f"   ビジュアル要素: {analysis_results['summary']['total_visual_elements']}個 ({'✅ 成功' if analysis_results['summary']['visual_elements_extraction_success'] else '❌ 失敗'})")
        
        return analysis_results
    
    def _resolve_coordinates_from_page_anchor(self, page_anchor, document):
        """page_anchorから座標を解決（リファレンス準拠の正しい方法）"""
        coordinates = []
        
        try:
            # page_anchorの各属性を確認してpage参照を解決
            page_refs = []
            
            # 一般的なpage参照属性名を試行
            for attr_name in ['page_refs', 'page_ref', 'pages']:
                if hasattr(page_anchor, attr_name):
                    refs = getattr(page_anchor, attr_name)
                    if refs:
                        if hasattr(refs, '__iter__'):  # リストの場合
                            page_refs.extend(refs)
                        else:  # 単一要素の場合
                            page_refs.append(refs)
            
            # page参照からdocument.pagesの対応する要素を探して座標を取得
            for page_ref in page_refs:
                # page_refオブジェクトの属性を確認
                ref_attrs = dir(page_ref)
                
                # ページ番号や要素インデックスを取得
                page_num = None
                element_index = None
                
                for attr in ['page', 'page_number', 'page_index']:
                    if hasattr(page_ref, attr):
                        page_num = getattr(page_ref, attr)
                        break
                
                for attr in ['element', 'element_index', 'block_index', 'index']:
                    if hasattr(page_ref, attr):
                        element_index = getattr(page_ref, attr)
                        break
                
                # document.pagesから対応する要素を取得
                if page_num is not None and hasattr(document, 'pages') and document.pages:
                    # ページ番号は1-indexedの可能性があるため調整
                    page_idx = page_num - 1 if page_num > 0 else page_num
                    
                    if 0 <= page_idx < len(document.pages):
                        page = document.pages[page_idx]
                        
                        # 各要素タイプから座標を取得
                        for element_type in ['blocks', 'paragraphs', 'lines', 'tokens']:
                            if hasattr(page, element_type):
                                elements = getattr(page, element_type)
                                if elements and element_index is not None and 0 <= element_index < len(elements):
                                    element = elements[element_index]
                                    if hasattr(element, 'layout') and element.layout:
                                        layout = element.layout
                                        if hasattr(layout, 'bounding_poly') and layout.bounding_poly:
                                            bp = layout.bounding_poly
                                            if hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                                                vertices = []
                                                for vertex in bp.normalized_vertices:
                                                    vertices.append({
                                                        "x": getattr(vertex, 'x', 0),
                                                        "y": getattr(vertex, 'y', 0)
                                                    })
                                                coordinates.append({
                                                    "source": f"page_{page_num}_{element_type}_{element_index}",
                                                    "coordinates": vertices
                                                })
        except Exception as e:
            print(f"       ⚠️ page_anchor座標解決エラー: {e}")
        
        return coordinates
    
    def _check_processor_info(self):
        """プロセッサの詳細情報を取得して確認"""
        try:
            print("\n🔍 プロセッサ情報確認中...")
            
            # プロセッサの詳細情報を取得
            processor = self.client.get_processor(name=self.processor_name)
            
            print(f"   プロセッサタイプ: {processor.type_}")
            print(f"   プロセッサ名: {processor.display_name}")
            print(f"   プロセッサバージョン: {processor.process_endpoint}")
            print(f"   作成日時: {processor.create_time}")
            print(f"   最終更新: {processor.update_time}")
            print(f"   状態: {processor.state}")
            
            # サポートされている機能を調査
            print(f"   プロセッサID: {processor.name}")
            
        except Exception as e:
            print(f"   ⚠️  プロセッサ情報取得エラー: {e}")
    
    def _extract_page_coordinates(self, page, page_data, full_text):
        """ページから座標情報を抽出 - 詳細調査版"""
        coordinates_found = False
        
        print(f"    🎯 座標抽出 (document.pages[].blocks[].layout.bounding_poly):")
        
        # 1. document.pages[].blocks を詳細調査
        if hasattr(page, 'blocks') and page.blocks:
            print(f"       blocks: {len(page.blocks)}個")
            
            for block_idx, block in enumerate(page.blocks):
                print(f"         ブロック{block_idx+1}調査:")
                
                # ブロックの基本属性を確認
                block_attrs = dir(block)
                relevant_attrs = [attr for attr in block_attrs if not attr.startswith('_')]
                print(f"           属性: {relevant_attrs[:10]}...")  # 最初の10個のみ表示
                
                if hasattr(block, 'layout') and block.layout:
                    print(f"           layout: 存在")
                    layout = block.layout
                    
                    # レイアウトの属性も調査
                    layout_attrs = dir(layout)
                    layout_relevant = [attr for attr in layout_attrs if not attr.startswith('_')]
                    print(f"           layout属性: {layout_relevant[:10]}...")
                    
                    # バウンディングポリゴンを詳細調査
                    if hasattr(layout, 'bounding_poly'):
                        print(f"           bounding_poly: 存在")
                        bounding_poly = layout.bounding_poly
                        
                        if bounding_poly:
                            print(f"           bounding_poly: 有効")
                            bp_attrs = dir(bounding_poly)
                            bp_relevant = [attr for attr in bp_attrs if not attr.startswith('_')]
                            print(f"           bounding_poly属性: {bp_relevant}")
                            
                            # 各頂点タイプを確認
                            for vertex_type in ['normalized_vertices', 'vertices']:
                                if hasattr(bounding_poly, vertex_type):
                                    vertices = getattr(bounding_poly, vertex_type)
                                    print(f"           {vertex_type}: {len(vertices) if vertices else 0}個")
                                    
                                    if vertices and len(vertices) > 0:
                                        # 座標データを実際に取得
                                        coord_list = []
                                        for vertex in vertices:
                                            coord_list.append({
                                                "x": getattr(vertex, 'x', 0),
                                                "y": getattr(vertex, 'y', 0)
                                            })
                                        
                                        # テキストも同時に取得
                                        block_text = self._extract_text_from_layout(layout, full_text)
                                        
                                        coordinate_entry = {
                                            "block_id": block_idx + 1,
                                            "coordinates": coord_list,
                                            "coordinate_type": vertex_type,
                                            "text": block_text or "",
                                            "text_length": len(block_text) if block_text else 0
                                        }
                                        
                                        page_data["coordinates"].append(coordinate_entry)
                                        coordinates_found = True
                                        
                                        print(f"           ✅ 座標取得成功: {len(coord_list)}個, テキスト'{block_text[:30] if block_text else '(なし)'}...'")
                                        break
                        else:
                            print(f"           bounding_poly: None")
                    else:
                        print(f"           bounding_poly: 属性なし")
                else:
                    print(f"           layout: なし")
        
        # 2. 他の可能な座標ソースも調査
        print(f"\n    🔍 他の座標ソース調査:")
        
        # paragraphs
        if hasattr(page, 'paragraphs') and page.paragraphs:
            print(f"       paragraphs: {len(page.paragraphs)}個")
            for i, para in enumerate(page.paragraphs[:3]):  # 最初の3個のみ
                if hasattr(para, 'layout') and para.layout and hasattr(para.layout, 'bounding_poly'):
                    bp = para.layout.bounding_poly
                    if bp and hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                        print(f"         段落{i+1}: 座標{len(bp.normalized_vertices)}個あり")
        
        # lines
        if hasattr(page, 'lines') and page.lines:
            print(f"       lines: {len(page.lines)}個")
            for i, line in enumerate(page.lines[:3]):  # 最初の3個のみ
                if hasattr(line, 'layout') and line.layout and hasattr(line.layout, 'bounding_poly'):
                    bp = line.layout.bounding_poly
                    if bp and hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                        print(f"         行{i+1}: 座標{len(bp.normalized_vertices)}個あり")
        
        # tokens
        if hasattr(page, 'tokens') and page.tokens:
            print(f"       tokens: {len(page.tokens)}個")
            for i, token in enumerate(page.tokens[:3]):  # 最初の3個のみ
                if hasattr(token, 'layout') and token.layout and hasattr(token.layout, 'bounding_poly'):
                    bp = token.layout.bounding_poly
                    if bp and hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                        print(f"         トークン{i+1}: 座標{len(bp.normalized_vertices)}個あり")
        
        if not coordinates_found:
            print(f"       ❌ 全ての調査で座標情報なし")
        else:
            print(f"       ✅ 座標抽出成功: {len(page_data['coordinates'])}個")
        
        return coordinates_found
    
    def deep_investigate_image_blocks(self, document):
        """image_block 属性の構造を詳細に調査する"""
        
        print(f"\n🔬 image_block 詳細構造調査:")
        print("=" * 50)
        
        if not hasattr(document, 'document_layout') or not document.document_layout.blocks:
            print("❌ document_layout.blocks が存在しません")
            return []
        
        image_findings = []
        blocks = document.document_layout.blocks
        
        for i, block in enumerate(blocks):
            print(f"\n📋 ブロック {i+1} 調査:")
            
            # 🎯 image_block の存在と中身を徹底調査
            if hasattr(block, 'image_block'):
                image_block = getattr(block, 'image_block')
                print(f"   image_block: {bool(image_block)} ({type(image_block)})")
                
                if image_block:  # 実際に値がある場合
                    print(f"   📸 ✅ ブロック {i+1} は image_block を持っています！")
                    
                    # image_block の属性（名前）をリストアップ
                    img_attrs = [a for a in dir(image_block) if not a.startswith('_')]
                    print(f"      属性リスト: {img_attrs}")
                    
                    # 各属性の値を詳細調査
                    image_block_data = {}
                    for attr in img_attrs:
                        try:
                            attr_value = getattr(image_block, attr)
                            attr_type = type(attr_value).__name__
                            
                            # バイナリデータの場合は長さのみ表示
                            if isinstance(attr_value, bytes):
                                print(f"      {attr}: {attr_type} ({len(attr_value)} bytes)")
                                image_block_data[attr] = f"bytes_length_{len(attr_value)}"
                            elif isinstance(attr_value, str) and len(attr_value) > 100:
                                print(f"      {attr}: {attr_type} ({len(attr_value)} chars)")
                                image_block_data[attr] = f"string_length_{len(attr_value)}"
                            else:
                                print(f"      {attr}: {attr_type} = {str(attr_value)[:200]}")
                                image_block_data[attr] = str(attr_value)[:200]
                        except Exception as e:
                            print(f"      {attr}: エラー - {e}")
                            image_block_data[attr] = f"error: {e}"
                    
                    # 🎯 座標（住所）がどこにあるか探す
                    coordinates_found = []
                    
                    # 方法1: block.bounding_box から
                    if hasattr(block, 'bounding_box') and block.bounding_box:
                        bbox = block.bounding_box
                        print(f"      🎯 bounding_box: 存在")
                        
                        for vertex_attr in ['normalized_vertices', 'vertices']:
                            if hasattr(bbox, vertex_attr):
                                vertices = getattr(bbox, vertex_attr)
                                if vertices and len(vertices) >= 4:
                                    coords = [(v.x, v.y) for v in vertices]
                                    coordinates_found.append({
                                        "source": f"block.bounding_box.{vertex_attr}",
                                        "coordinates": coords
                                    })
                                    print(f"         ✅ 座標発見 ({vertex_attr}): {coords[0]} → {coords[2]}")
                    
                    # 方法2: image_block 内の座標属性
                    for coord_attr in ['bounding_box', 'bounding_poly', 'layout', 'coordinates']:
                        if hasattr(image_block, coord_attr):
                            coord_obj = getattr(image_block, coord_attr)
                            if coord_obj:
                                print(f"      🎯 image_block.{coord_attr}: 存在")
                                
                                # 座標オブジェクトの詳細調査
                                if hasattr(coord_obj, 'normalized_vertices'):
                                    vertices = coord_obj.normalized_vertices
                                    if vertices and len(vertices) >= 4:
                                        coords = [(v.x, v.y) for v in vertices]
                                        coordinates_found.append({
                                            "source": f"image_block.{coord_attr}.normalized_vertices",
                                            "coordinates": coords
                                        })
                                        print(f"         ✅ 座標発見 (image_block): {coords[0]} → {coords[2]}")
                    
                    # 🆕 方法3: blob_assetsからの実画像データ取得
                    blob_id = getattr(image_block, 'blob_asset_id', '')
                    if blob_id:
                        print(f"      🎯 blob_asset_id: {blob_id}")
                        
                        # documentからblob_assetsを探す
                        if hasattr(document, 'blob_assets') and document.blob_assets:
                            for blob_asset in document.blob_assets:
                                if getattr(blob_asset, 'asset_id', '') == blob_id:
                                    print(f"      ✅ blob_asset発見: {blob_id}")
                                    
                                    # 実際の画像データ取得
                                    if hasattr(blob_asset, 'content') and blob_asset.content:
                                        image_data = blob_asset.content
                                        mime_type = getattr(blob_asset, 'mime_type', 'image/png')
                                        
                                        # 画像保存
                                        try:
                                            import os
                                            images_dir = "extracted_images"
                                            if not os.path.exists(images_dir):
                                                os.makedirs(images_dir)
                                            
                                            image_filename = f"image_block_{i+1}_{blob_id}.png"
                                            image_path = os.path.join(images_dir, image_filename)
                                            
                                            with open(image_path, 'wb') as f:
                                                f.write(image_data)
                                            
                                            print(f"         ✅ 画像保存成功: {image_path}")
                                            print(f"         📊 画像サイズ: {len(image_data)} bytes")
                                            
                                            # image_block_dataに追加
                                            image_block_data['extracted_image_path'] = image_path
                                            image_block_data['extracted_image_size'] = len(image_data)
                                            
                                        except Exception as e:
                                            print(f"         ❌ 画像保存エラー: {e}")
                                    break
                    
                    # ブロック種類の再確認
                    block_type = "unknown"
                    for type_attr in ['type', 'block_type', 'layout_type']:
                        if hasattr(block, type_attr):
                            block_type = getattr(block, type_attr)
                            print(f"      種類 ({type_attr}): {block_type}")
                            break
                    
                    # 発見情報をまとめ
                    finding = {
                        "block_index": i + 1,
                        "has_image_block": True,
                        "image_block_attributes": img_attrs,
                        "image_block_data": image_block_data,
                        "coordinates_found": coordinates_found,
                        "block_type": block_type,
                        "coordinate_count": len(coordinates_found)
                    }
                    
                    image_findings.append(finding)
                    
                else:
                    print(f"   image_block: False または空")
            else:
                print(f"   image_block: 属性なし")
            
            # テキストブロック情報も参考として表示
            if hasattr(block, 'text_block') and block.text_block:
                text_content = getattr(block.text_block, 'text', '')
                print(f"   text_block: あり ('{text_content[:30]}...')")
        
        # 調査結果サマリー
        print(f"\n📊 image_block 調査結果:")
        print(f"   総ブロック数: {len(blocks)}")
        print(f"   image_block保有: {len(image_findings)}個")
        
        for finding in image_findings:
            print(f"   ブロック{finding['block_index']}: 座標{finding['coordinate_count']}セット, 属性{len(finding['image_block_attributes'])}個")
        
        return image_findings
    
    def investigate_pages_blocks_coordinates(self, document):
        """document.pages[].blocks と paragraphs の座標を詳細調査"""
        
        print(f"\n🎯 pages.blocks 座標詳細調査:")
        print("=" * 50)
        
        coordinates_findings = []
        
        if not hasattr(document, 'pages') or not document.pages:
            print("❌ document.pages が存在しません")
            return coordinates_findings
        
        for page_idx, page in enumerate(document.pages):
            print(f"\n📄 ページ {page_idx + 1} 詳細調査:")
            
            page_finding = {
                "page_index": page_idx + 1,
                "blocks_with_coordinates": [],
                "paragraphs_with_coordinates": [],
                "lines_with_coordinates": [],
                "tokens_with_coordinates": []
            }
            
            # 🔍 1. pages[].blocks の徹底調査
            if hasattr(page, 'blocks'):
                blocks = page.blocks
                print(f"   📋 blocks: {len(blocks)}個")
                
                for block_idx, block in enumerate(blocks):
                    print(f"      ブロック{block_idx+1}:")
                    
                    # ブロック属性調査
                    block_attrs = [attr for attr in dir(block) if not attr.startswith('_')]
                    print(f"        属性: {block_attrs[:10]}...")
                    
                    # 🎯 layout.bounding_poly を詳細調査
                    if hasattr(block, 'layout') and block.layout:
                        layout = block.layout
                        print(f"        layout: ✅ 存在")
                        
                        if hasattr(layout, 'bounding_poly') and layout.bounding_poly:
                            bp = layout.bounding_poly
                            print(f"        bounding_poly: ✅ 存在")
                            
                            if hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                                vertices = bp.normalized_vertices
                                if vertices and len(vertices) >= 4:
                                    coords = [(v.x, v.y) for v in vertices]
                                    print(f"        🎯 座標発見: {coords[0]} → {coords[2]}")
                                    
                                    # テキスト取得
                                    block_text = ""
                                    if hasattr(layout, 'text_anchor') and layout.text_anchor:
                                        text_anchor = layout.text_anchor
                                        if hasattr(text_anchor, 'text_segments') and text_anchor.text_segments:
                                            segment = text_anchor.text_segments[0]
                                            start_idx = getattr(segment, 'start_index', 0)
                                            end_idx = getattr(segment, 'end_index', 0)
                                            full_text = getattr(document, 'text', '')
                                            if full_text:
                                                block_text = full_text[start_idx:end_idx]
                                    
                                    block_coord_info = {
                                        "block_index": block_idx + 1,
                                        "coordinates": coords,
                                        "text": block_text,
                                        "source": "pages.blocks.layout.bounding_poly"
                                    }
                                    
                                    page_finding["blocks_with_coordinates"].append(block_coord_info)
                                    print(f"        テキスト: '{block_text[:30]}...'")
                                else:
                                    print(f"        normalized_vertices: {len(vertices) if vertices else 0}個（不完全）")
                            else:
                                print(f"        normalized_vertices: なし")
                        else:
                            print(f"        bounding_poly: なし")
                    else:
                        print(f"        layout: なし")
            else:
                print(f"   📋 blocks: 属性なし")
            
            # 🔍 2. pages[].paragraphs の徹底調査
            if hasattr(page, 'paragraphs'):
                paragraphs = page.paragraphs
                print(f"   📝 paragraphs: {len(paragraphs)}個")
                
                for para_idx, paragraph in enumerate(paragraphs):
                    print(f"      段落{para_idx+1}:")
                    
                    if hasattr(paragraph, 'layout') and paragraph.layout:
                        layout = paragraph.layout
                        print(f"        layout: ✅ 存在")
                        
                        if hasattr(layout, 'bounding_poly') and layout.bounding_poly:
                            bp = layout.bounding_poly
                            if hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                                vertices = bp.normalized_vertices
                                if vertices and len(vertices) >= 4:
                                    coords = [(v.x, v.y) for v in vertices]
                                    print(f"        🎯 段落座標発見: {coords[0]} → {coords[2]}")
                                    
                                    # テキスト取得
                                    para_text = ""
                                    if hasattr(layout, 'text_anchor') and layout.text_anchor:
                                        text_anchor = layout.text_anchor
                                        if hasattr(text_anchor, 'text_segments') and text_anchor.text_segments:
                                            segment = text_anchor.text_segments[0]
                                            start_idx = getattr(segment, 'start_index', 0)
                                            end_idx = getattr(segment, 'end_index', 0)
                                            full_text = getattr(document, 'text', '')
                                            if full_text:
                                                para_text = full_text[start_idx:end_idx]
                                    
                                    para_coord_info = {
                                        "paragraph_index": para_idx + 1,
                                        "coordinates": coords,
                                        "text": para_text,
                                        "source": "pages.paragraphs.layout.bounding_poly"
                                    }
                                    
                                    page_finding["paragraphs_with_coordinates"].append(para_coord_info)
                                    print(f"        テキスト: '{para_text[:30]}...'")
            else:
                print(f"   📝 paragraphs: 属性なし")
            
            # 🔍 3. pages[].lines の調査（補足）
            if hasattr(page, 'lines') and page.lines:
                print(f"   📏 lines: {len(page.lines)}個")
                
                for line_idx, line in enumerate(page.lines[:3]):  # 最初の3行のみ
                    if hasattr(line, 'layout') and line.layout and hasattr(line.layout, 'bounding_poly'):
                        bp = line.layout.bounding_poly
                        if hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                            vertices = bp.normalized_vertices
                            if vertices and len(vertices) >= 4:
                                coords = [(v.x, v.y) for v in vertices]
                                
                                line_coord_info = {
                                    "line_index": line_idx + 1,
                                    "coordinates": coords,
                                    "source": "pages.lines.layout.bounding_poly"
                                }
                                
                                page_finding["lines_with_coordinates"].append(line_coord_info)
                                print(f"      行{line_idx+1}: 座標あり")
            
            coordinates_findings.append(page_finding)
        
        # 🎯 調査結果サマリー
        print(f"\n📊 pages 座標調査結果:")
        total_blocks_coords = sum(len(pf["blocks_with_coordinates"]) for pf in coordinates_findings)
        total_paras_coords = sum(len(pf["paragraphs_with_coordinates"]) for pf in coordinates_findings)
        total_lines_coords = sum(len(pf["lines_with_coordinates"]) for pf in coordinates_findings)
        
        print(f"   blocks座標: {total_blocks_coords}個")
        print(f"   paragraphs座標: {total_paras_coords}個")
        print(f"   lines座標: {total_lines_coords}個")
        
        return coordinates_findings
    
    def extract_from_pages_blocks(self, document, page_index, page_blocks_findings):
        """pages.blocks で見つかった座標を使って個別画像を切り抜く"""
        
        print(f"\n🎯 pages.blocks座標による画像切り抜き (ページ{page_index+1}):")
        print("-" * 50)
        
        extracted_figures = []
        
        # ページ全体画像を取得
        if not hasattr(document, 'pages') or page_index >= len(document.pages):
            print("❌ ページが存在しません")
            return extracted_figures
        
        page = document.pages[page_index]
        if not hasattr(page, 'image') or not page.image or not page.image.content:
            print("❌ ページ画像が存在しません")
            return extracted_figures
        
        try:
            # 画像データ取得
            if isinstance(page.image.content, str):
                import base64
                image_data = base64.b64decode(page.image.content)
            else:
                image_data = page.image.content
            
            whole_image = Image.open(io.BytesIO(image_data))
            width, height = whole_image.size
            
            print(f"✅ ページ全体画像: {width}x{height}px")
            
            # 対応するページの座標データを取得
            if page_index < len(page_blocks_findings):
                page_finding = page_blocks_findings[page_index]
                
                # blocks座標から切り抜き
                blocks_coords = page_finding["blocks_with_coordinates"]
                print(f"📋 blocks座標: {len(blocks_coords)}個")
                
                for block_coord in blocks_coords:
                    coords = block_coord["coordinates"]
                    text = block_coord["text"]
                    
                    # 座標をピクセルに変換
                    left = int(coords[0][0] * width)
                    top = int(coords[0][1] * height)
                    right = int(coords[2][0] * width)
                    bottom = int(coords[2][1] * height)
                    
                    print(f"   ブロック{block_coord['block_index']}: ({left}, {top}) → ({right}, {bottom})")
                    print(f"   テキスト: '{text[:30]}...'")
                    
                    # 座標の妥当性チェック
                    if left >= right or top >= bottom or left < 0 or top < 0:
                        print(f"   ❌ 無効な座標")
                        continue
                    
                    # 画像切り抜き
                    try:
                        cropped_img = whole_image.crop((left, top, right, bottom))
                        
                        # 保存ディレクトリ確保
                        figures_dir = "extracted_figures"
                        if not os.path.exists(figures_dir):
                            os.makedirs(figures_dir)
                        
                        # 保存
                        save_path = os.path.join(figures_dir, f"block_page{page_index+1}_{block_coord['block_index']}.png")
                        cropped_img.save(save_path)
                        
                        # 結果記録
                        figure_info = {
                            "figure_id": block_coord['block_index'],
                            "coordinates": {
                                "left": left,
                                "top": top,
                                "right": right,
                                "bottom": bottom
                            },
                            "size": {
                                "width": right - left,
                                "height": bottom - top
                            },
                            "text": text,
                            "source": "pages.blocks.layout.bounding_poly",
                            "saved_path": save_path
                        }
                        
                        extracted_figures.append(figure_info)
                        print(f"   ✅ 切り抜き成功: {save_path}")
                        
                    except Exception as e:
                        print(f"   ❌ 切り抜きエラー: {e}")
                
                # paragraphs座標からも切り抜き
                paras_coords = page_finding["paragraphs_with_coordinates"]
                print(f"📝 paragraphs座標: {len(paras_coords)}個")
                
                for para_coord in paras_coords:
                    coords = para_coord["coordinates"]
                    text = para_coord["text"]
                    
                    # 座標をピクセルに変換
                    left = int(coords[0][0] * width)
                    top = int(coords[0][1] * height)
                    right = int(coords[2][0] * width)
                    bottom = int(coords[2][1] * height)
                    
                    print(f"   段落{para_coord['paragraph_index']}: ({left}, {top}) → ({right}, {bottom})")
                    print(f"   テキスト: '{text[:30]}...'")
                    
                    # 座標の妥当性チェック
                    if left >= right or top >= bottom or left < 0 or top < 0:
                        print(f"   ❌ 無効な座標")
                        continue
                    
                    # 画像切り抜き
                    try:
                        cropped_img = whole_image.crop((left, top, right, bottom))
                        
                        # 保存
                        save_path = os.path.join(figures_dir, f"paragraph_page{page_index+1}_{para_coord['paragraph_index']}.png")
                        cropped_img.save(save_path)
                        
                        # 結果記録
                        figure_info = {
                            "figure_id": para_coord['paragraph_index'],
                            "coordinates": {
                                "left": left,
                                "top": top,
                                "right": right,
                                "bottom": bottom
                            },
                            "size": {
                                "width": right - left,
                                "height": bottom - top
                            },
                            "text": text,
                            "source": "pages.paragraphs.layout.bounding_poly",
                            "saved_path": save_path
                        }
                        
                        extracted_figures.append(figure_info)
                        print(f"   ✅ 段落切り抜き成功: {save_path}")
                        
                    except Exception as e:
                        print(f"   ❌ 段落切り抜きエラー: {e}")
            
            print(f"\n📊 pages.blocks切り抜き結果: {len(extracted_figures)}個")
            
        except Exception as e:
            print(f"❌ 全体的なエラー: {e}")
        
        return extracted_figures
    
    def extract_individual_images(self, document, page_index=0):
        """ページ内の個別要素（椅子や人物のイラスト）を切り抜いて保存する - document_layout対応版"""
        
        print(f"\n🔍 個別画像切り抜き処理開始 (ページ{page_index+1}):")
        print("-" * 40)
        
        extracted_images = []
        
        # 1. ページ全体の画像データを読み込む（従来通りpages[].imageから）
        if not hasattr(document, 'pages') or not document.pages:
            print("❌ document.pagesが存在しません")
            return extracted_images
        
        if page_index >= len(document.pages):
            print(f"❌ ページ{page_index+1}が存在しません（総ページ数: {len(document.pages)}）")
            return extracted_images
        
        page = document.pages[page_index]
        
        if not hasattr(page, 'image') or not page.image or not page.image.content:
            print("❌ ページ画像が見つかりません。return_images=Trueを確認してください。")
            return extracted_images
        
        try:
            # base64デコードまたは直接バイナリデータとして処理
            if isinstance(page.image.content, str):
                import base64
                image_data = base64.b64decode(page.image.content)
            else:
                image_data = page.image.content
            
            whole_image = Image.open(io.BytesIO(image_data))
            width, height = whole_image.size
            
            print(f"✅ ページ全体画像読み込み成功: {width}x{height}px")
            
            # 2. 🆕 document_layout.blocks を探索（最新プロセッサ対応）
            if not (hasattr(document, 'document_layout') and document.document_layout and 
                   hasattr(document.document_layout, 'blocks') and document.document_layout.blocks):
                print("❌ document_layout.blocksが存在しません")
                return extracted_images
            
            blocks = document.document_layout.blocks
            print(f"🔍 document_layout.blocks調査: {len(blocks)}個")
            
            # 🆕 チャンクデータからの画像情報調査も追加
            chunk_image_candidates = []
            if hasattr(document, 'chunked_document') and document.chunked_document:
                chunks = document.chunked_document.chunks
                print(f"🔍 chunked_document追加調査: {len(chunks)}個のチャンク")
                
                for chunk_idx, chunk in enumerate(chunks):
                    # チャンクに画像データが含まれているかチェック
                    chunk_content = getattr(chunk, 'content', '')
                    if 'image' in chunk_content.lower() or 'figure' in chunk_content.lower() or 'chair' in chunk_content.lower():
                        print(f"  チャンク{chunk_idx+1}: 画像関連キーワード検出")
                        chunk_image_candidates.append(chunk_idx)
            
            figure_count = 0
            for i, block in enumerate(blocks):
                print(f"\n  ブロック{i+1}:")
                
                # ブロックの詳細属性を調査
                block_attrs = [attr for attr in dir(block) if not attr.startswith('_')]
                print(f"    利用可能属性: {block_attrs[:15]}...")  # 最初の15個のみ表示
                
                # ブロックタイプを確認
                block_type = None
                for type_attr in ['type', 'block_type', 'layout_type']:
                    if hasattr(block, type_attr):
                        block_type = getattr(block, type_attr)
                        print(f"    {type_attr}: {block_type}")
                        break
                
                # 🎯 figureブロック（画像/図解）を検出
                is_figure_block = False
                
                # 方法1: typeが"figure"や"FIGURE"
                if block_type and str(block_type).lower() in ['figure', 'image']:
                    is_figure_block = True
                    print(f"    ✅ 図解ブロック検出: {block_type}")
                
                # 方法2: image_blockの存在確認
                elif hasattr(block, 'image_block') and block.image_block:
                    is_figure_block = True
                    print(f"    ✅ image_block検出")
                
                # 🆕 方法3: 各ブロック属性の詳細調査（debug）
                else:
                    print(f"    🔍 ブロック詳細調査:")
                    
                    # 各ブロックタイプの属性値を確認
                    for block_type_attr in ['image_block', 'list_block', 'table_block']:
                        if hasattr(block, block_type_attr):
                            attr_value = getattr(block, block_type_attr)
                            print(f"      {block_type_attr}: {bool(attr_value)}")
                            
                            # image_blockが存在する場合、さらに詳細を調査
                            if block_type_attr == 'image_block' and attr_value:
                                print(f"        image_block詳細: {type(attr_value)}")
                                img_attrs = [attr for attr in dir(attr_value) if not attr.startswith('_')]
                                print(f"        image_block属性: {img_attrs[:10]}...")
                                is_figure_block = True
                                break
                    
                    # テキスト以外のブロックを画像候補として扱う
                    if not (hasattr(block, 'text_block') and block.text_block):
                        print(f"    🔍 非テキストブロック - 画像候補として調査")
                        is_figure_block = True
                
                if is_figure_block:
                    figure_count += 1
                    print(f"    🎯 図解要素{figure_count} - 座標取得試行")
                    
                    # 座標取得の多方面アプローチ
                    coordinates_found = False
                    coord_source = ""
                    vertices = None
                    
                    # 座標取得方法1: block.bounding_box
                    if hasattr(block, 'bounding_box') and block.bounding_box:
                        bbox = block.bounding_box
                        print(f"      bounding_box: 存在")
                        
                        # bounding_boxの詳細属性を調査
                        bbox_attrs = [attr for attr in dir(bbox) if not attr.startswith('_')]
                        print(f"      bounding_box属性: {bbox_attrs}")
                        
                        for vertex_attr in ['normalized_vertices', 'vertices']:
                            if hasattr(bbox, vertex_attr):
                                vertices = getattr(bbox, vertex_attr)
                                if vertices and len(vertices) >= 4:
                                    coordinates_found = True
                                    coord_source = f"bounding_box.{vertex_attr}"
                                    print(f"      ✅ 座標取得成功: {coord_source}")
                                    break
                                else:
                                    print(f"      bounding_box.{vertex_attr}: {len(vertices) if vertices else 0}個（不完全）")
                    else:
                        print(f"      bounding_box: なし")
                    
                    # 座標取得方法2: block.layout.bounding_poly（後方互換）
                    if not coordinates_found and hasattr(block, 'layout') and block.layout:
                        layout = block.layout
                        print(f"      layout: 存在")
                        
                        if hasattr(layout, 'bounding_poly') and layout.bounding_poly:
                            bp = layout.bounding_poly
                            if hasattr(bp, 'normalized_vertices') and bp.normalized_vertices:
                                vertices = bp.normalized_vertices
                                if vertices and len(vertices) >= 4:
                                    coordinates_found = True
                                    coord_source = "layout.bounding_poly.normalized_vertices"
                                    print(f"      ✅ 座標取得成功: {coord_source}")
                    
                    if coordinates_found:
                        # 割合(0.0-1.0)をピクセル(px)に変換
                        left = int(vertices[0].x * width)
                        top = int(vertices[0].y * height)
                        right = int(vertices[2].x * width)
                        bottom = int(vertices[2].y * height)
                        
                        # 座標の妥当性チェック
                        if left >= right or top >= bottom or left < 0 or top < 0:
                            print(f"      ❌ 無効な座標: ({left}, {top}) - ({right}, {bottom})")
                            continue
                        
                        print(f"      📐 座標: 左上({left}, {top}) → 右下({right}, {bottom})")
                        print(f"      📏 サイズ: {right-left}x{bottom-top}px")
                        
                        # 3. 画像を切り抜く
                        try:
                            cropped_img = whole_image.crop((left, top, right, bottom))
                            
                            # 保存ディレクトリ確保
                            figures_dir = "extracted_figures"
                            if not os.path.exists(figures_dir):
                                os.makedirs(figures_dir)
                            
                            # 保存
                            save_path = os.path.join(figures_dir, f"figure_page{page_index+1}_{figure_count}.png")
                            cropped_img.save(save_path)
                            
                            # 結果記録
                            figure_info = {
                                "figure_id": figure_count,
                                "block_index": i + 1,
                                "coordinates": {
                                    "left": left,
                                    "top": top,
                                    "right": right,
                                    "bottom": bottom
                                },
                                "size": {
                                    "width": right - left,
                                    "height": bottom - top
                                },
                                "coordinate_source": coord_source,
                                "saved_path": save_path
                            }
                            
                            extracted_images.append(figure_info)
                            
                            print(f"      ✅ 個別画像保存成功: {save_path}")
                            
                        except Exception as crop_error:
                            print(f"      ❌ 画像切り抜きエラー: {crop_error}")
                    
                    else:
                        print(f"      ❌ 座標情報取得失敗")
                
                else:
                    print(f"    ℹ️ テキストブロック（スキップ）")
            
            print(f"\n📊 切り抜き結果:")
            print(f"   総ブロック: {len(blocks)}個")
            print(f"   図解候補: {figure_count}個")
            print(f"   切り抜き成功: {len(extracted_images)}個")
            
        except Exception as e:
            print(f"❌ 画像処理エラー: {e}")
        
        return extracted_images
    
    def _extract_page_image_data(self, page, page_data):
        """ページから画像データを抽出し、ファイルとして保存"""
        
        print(f"    🖼️  画像抽出 (document.pages[].image):")
        
        if hasattr(page, 'image') and page.image:
            image = page.image
            
            # 画像の基本情報
            image_info = {
                "has_content": bool(hasattr(image, 'content') and image.content),
                "content_size": len(image.content) if hasattr(image, 'content') and image.content else 0,
                "mime_type": getattr(image, 'mime_type', ''),
                "width": getattr(image, 'width', 0),
                "height": getattr(image, 'height', 0)
            }
            
            # 画像ファイルとして保存
            if hasattr(image, 'content') and image.content:
                import base64
                import os
                
                # 保存ディレクトリ作成
                images_dir = "extracted_images"
                if not os.path.exists(images_dir):
                    os.makedirs(images_dir)
                
                # ファイル名生成
                page_num = page_data["page"]
                image_filename = f"layout_parser_page_{page_num}.png"
                image_path = os.path.join(images_dir, image_filename)
                
                try:
                    # base64デコードして保存
                    if isinstance(image.content, str):
                        # 文字列の場合はbase64デコード
                        image_data = base64.b64decode(image.content)
                    else:
                        # バイナリデータの場合はそのまま
                        image_data = image.content
                    
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                    
                    image_info["saved_file"] = image_path
                    image_info["file_saved"] = True
                    
                    print(f"       ✅ 画像ファイル保存成功: {image_path}")
                    
                except Exception as e:
                    image_info["save_error"] = str(e)
                    image_info["file_saved"] = False
                    print(f"       ❌ 画像ファイル保存エラー: {e}")
            
            page_data["image_data"] = image_info
            
            print(f"       ✅ 画像データあり:")
            print(f"         サイズ: {image_info['content_size']} bytes")
            print(f"         解像度: {image_info['width']}x{image_info['height']}")
            print(f"         MIME: {image_info['mime_type']}")
            
            return True
        else:
            print(f"       ❌ 画像データなし")
            page_data["image_data"] = {"has_content": False}
            return False
    
    def _extract_page_visual_elements(self, page, page_data):
        """ページからビジュアル要素を抽出"""
        
        print(f"    👁️  ビジュアル要素抽出 (document.pages[].visual_elements):")
        
        visual_elements_found = False
        
        if hasattr(page, 'visual_elements') and page.visual_elements:
            print(f"       visual_elements: {len(page.visual_elements)}個")
            
            for i, element in enumerate(page.visual_elements):
                element_info = {
                    "element_id": i + 1,
                    "type": getattr(element, 'type', ''),
                    "layout": {}
                }
                
                # レイアウト情報
                if hasattr(element, 'layout') and element.layout:
                    layout = element.layout
                    
                    if hasattr(layout, 'bounding_poly') and layout.bounding_poly:
                        if hasattr(layout.bounding_poly, 'normalized_vertices') and layout.bounding_poly.normalized_vertices:
                            vertices = []
                            for vertex in layout.bounding_poly.normalized_vertices:
                                vertices.append({
                                    "x": getattr(vertex, 'x', 0),
                                    "y": getattr(vertex, 'y', 0)
                                })
                            element_info["layout"]["coordinates"] = vertices
                
                page_data["visual_elements"].append(element_info)
                visual_elements_found = True
                
                print(f"         要素{i+1}: タイプ'{element_info['type']}', 座標{len(element_info.get('layout', {}).get('coordinates', []))}個")
        
        if not visual_elements_found:
            print(f"       ❌ ビジュアル要素なし")
        else:
            print(f"       ✅ ビジュアル要素抽出成功: {len(page_data['visual_elements'])}個")
        
        return visual_elements_found
    
    def _analyze_document_structure(self, document):
        """文書構造の詳細解析"""
        
        print("📋 Document構造解析:")
        print("-" * 30)
        
        # 基本属性確認（高度オプション対応）
        attributes = [
            ('text', 'document.text'),
            ('pages', 'document.pages'),
            ('entities', 'document.entities'),
            ('document_layout', 'document.document_layout'),
            ('paragraphs', 'document.paragraphs'),
            ('tables', 'document.tables'),
            ('form_fields', 'document.form_fields'),
            ('chunked_document', 'document.chunked_document'),  # チャンキング結果
            ('revisions', 'document.revisions'),  # リビジョン情報
        ]
        
        for attr, desc in attributes:
            if hasattr(document, attr):
                obj = getattr(document, attr)
                if obj is not None:
                    if isinstance(obj, str):
                        print(f"  ✅ {desc}: {len(obj)}文字")
                        if len(obj) > 0:
                            print(f"     先頭50文字: '{obj[:50]}...'")
                    else:
                        try:
                            print(f"  ✅ {desc}: {len(obj)}個の要素")
                        except:
                            print(f"  ✅ {desc}: オブジェクト存在（要素数取得不可）")
                else:
                    print(f"  ⚠️ {desc}: None")
            else:
                print(f"  ❌ {desc}: 属性なし")
        
        # チャンキング結果の詳細確認
        if hasattr(document, 'chunked_document') and document.chunked_document:
            chunks = document.chunked_document.chunks
            print(f"\n📦 チャンキング結果詳細:")
            print(f"   総チャンク数: {len(chunks)}個")
            
            for i, chunk in enumerate(chunks[:5]):  # 最初の5チャンクのみ表示
                chunk_text = getattr(chunk, 'content', '')
                chunk_page = getattr(chunk, 'page_headers', [])
                print(f"   チャンク{i+1}: {len(chunk_text)}文字")
                if chunk_text:
                    print(f"     内容: {chunk_text[:100]}...")
                if chunk_page:
                    print(f"     ページヘッダー: {len(chunk_page)}個")
        
        print()
    
    def _extract_all_text_methods(self, document):
        """全テキスト抽出手法を試行"""
        
        print("📄 テキスト抽出手法比較:")
        print("-" * 30)
        
        extraction_results = {}
        
        # 方法1: document.text
        if hasattr(document, 'text') and document.text:
            extraction_results['document.text'] = document.text
        else:
            extraction_results['document.text'] = ""
        
        # 方法2: document_layout.blocks
        blocks_text = []
        if hasattr(document, 'document_layout') and document.document_layout:
            print(f"  document_layout.blocks: {len(document.document_layout.blocks)}個")
            for i, block in enumerate(document.document_layout.blocks):
                if hasattr(block, 'text_block') and block.text_block:
                    block_text = block.text_block.text
                    if block_text and block_text.strip():
                        blocks_text.append(block_text.strip())
                        print(f"    ブロック{i+1}: '{block_text[:30]}...' ({len(block_text)}文字)")
        
        extraction_results['document_layout.blocks'] = "\n".join(blocks_text)
        
        # 方法3: pages詳細
        pages_all_text = []
        if hasattr(document, 'pages') and document.pages:
            print(f"  document.pages: {len(document.pages)}ページ")
            
            for page_idx, page in enumerate(document.pages):
                print(f"    ページ{page_idx+1}:")
                
                # ページの各要素を確認
                page_elements = {
                    'paragraphs': [],
                    'lines': [],
                    'tokens': [],
                    'blocks': []
                }
                
                # 段落
                if hasattr(page, 'paragraphs') and page.paragraphs:
                    print(f"      paragraphs: {len(page.paragraphs)}個")
                    for para in page.paragraphs:
                        if hasattr(para, 'layout') and para.layout:
                            para_text = self._extract_text_from_layout(para.layout, document.text or "")
                            if para_text:
                                page_elements['paragraphs'].append(para_text)
                
                # 行
                if hasattr(page, 'lines') and page.lines:
                    print(f"      lines: {len(page.lines)}個")
                    for line in page.lines:
                        if hasattr(line, 'layout') and line.layout:
                            line_text = self._extract_text_from_layout(line.layout, document.text or "")
                            if line_text:
                                page_elements['lines'].append(line_text)
                
                # トークン
                if hasattr(page, 'tokens') and page.tokens:
                    print(f"      tokens: {len(page.tokens)}個")
                    token_texts = []
                    for token in page.tokens[:50]:  # 最初の50トークンのみ
                        if hasattr(token, 'layout') and token.layout:
                            token_text = self._extract_text_from_layout(token.layout, document.text or "")
                            if token_text:
                                token_texts.append(token_text)
                    
                    if token_texts:
                        page_elements['tokens'] = [" ".join(token_texts)]
                        print(f"      トークン結合: '{' '.join(token_texts[:10])}...'")
                
                # ブロック
                if hasattr(page, 'blocks') and page.blocks:
                    print(f"      blocks: {len(page.blocks)}個")
                    for block in page.blocks:
                        if hasattr(block, 'layout') and block.layout:
                            block_text = self._extract_text_from_layout(block.layout, document.text or "")
                            if block_text:
                                page_elements['blocks'].append(block_text)
                
                # ページ内で最も多くのテキストを取得した方法を採用
                best_method = max(page_elements.keys(), key=lambda k: sum(len(text) for text in page_elements[k]))
                if page_elements[best_method]:
                    pages_all_text.extend(page_elements[best_method])
                    print(f"      採用方法: {best_method} ({sum(len(text) for text in page_elements[best_method])}文字)")
        
        extraction_results['pages.all'] = "\n".join(pages_all_text)
        
        # 結果比較
        print("\n📊 テキスト抽出結果比較:")
        print("-" * 30)
        for method, text in extraction_results.items():
            print(f"  {method}: {len(text)}文字")
            if text and len(text) > 0:
                print(f"    サンプル: '{text[:100]}...'")
        
        # 最も多くのテキストを抽出した方法
        best_overall = max(extraction_results.keys(), key=lambda k: len(extraction_results[k]))
        print(f"\n🏆 最適な抽出方法: {best_overall} ({len(extraction_results[best_overall])}文字)")
        
        return extraction_results
    
    def _extract_text_from_layout(self, layout, full_text):
        """レイアウトからテキストを抽出"""
        try:
            if hasattr(layout, 'text_anchor') and layout.text_anchor:
                text_anchor = layout.text_anchor
                if hasattr(text_anchor, 'text_segments') and text_anchor.text_segments:
                    segment = text_anchor.text_segments[0]
                    start_index = getattr(segment, 'start_index', 0)
                    end_index = getattr(segment, 'end_index', len(full_text))
                    return full_text[start_index:end_index]
        except:
            pass
        return ""
    
    def _save_detailed_results(self, document, extracted_figures=None, image_block_findings=None, layout_coordinates=None):
        """詳細結果をJSONで保存 - Layout Parser座標調査結果を含む"""
        
        # 適切なフィールド参照解析結果を取得
        field_reference_results = self._analyze_correct_field_references(document)
        
        # 🆕 個別画像切り抜き結果を追加
        individual_images_summary = {
            "total_extracted": len(extracted_figures) if extracted_figures else 0,
            "extraction_success": bool(extracted_figures and len(extracted_figures) > 0),
            "figures_details": extracted_figures if extracted_figures else []
        }
        
        # 🔬 image_block 詳細調査結果を追加
        image_block_investigation = {
            "blocks_with_image_block": len(image_block_findings) if image_block_findings else 0,
            "investigation_success": bool(image_block_findings and len(image_block_findings) > 0),
            "detailed_findings": image_block_findings if image_block_findings else []
        }
        
        # 🎯 Layout Parser座標調査結果を追加
        layout_coordinates_summary = {
            "total_coordinate_sets": len(layout_coordinates) if layout_coordinates else 0,
            "coordinate_extraction_success": bool(layout_coordinates and len(layout_coordinates) > 0),
            "coordinate_sources": layout_coordinates if layout_coordinates else []
        }
        image_block_investigation = {
            "blocks_with_image_block": len(image_block_findings) if image_block_findings else 0,
            "investigation_success": bool(image_block_findings and len(image_block_findings) > 0),
            "detailed_findings": image_block_findings if image_block_findings else []
        }
        
        results = {
            "timestamp": "2026-02-09",
            "processor": "Layout Parser v1beta3 - Coordinate Extraction Optimized",
            "api_version": "documentai_v1beta3",
            "field_reference_strategy": {
                "primary_coordinate_source": "document.pages[].blocks[].layout.bounding_poly",
                "image_data_source": "document.pages[].image", 
                "visual_elements_source": "document.pages[].visual_elements",
                "text_mapping_source": "layout.text_anchor.text_segments"
            },
            "advanced_options": {
                "chunkingConfig": {
                    "enabled": True,
                    "chunk_size": 500,
                    "include_ancestor_headings": True
                },
                "returnImages": True,
                "returnBoundingBoxes": True,
                "enableImageAnnotation": True,
                "enableImageExtraction": True,
                "enableTableAnnotation": True,
                "enableLlmLayoutParsing": False
            },
            "document_analysis": {
                "has_text": hasattr(document, 'text') and bool(document.text),
                "text_length": len(document.text) if hasattr(document, 'text') and document.text else 0,
                "has_pages": hasattr(document, 'pages') and bool(document.pages),
                "pages_count": len(document.pages) if hasattr(document, 'pages') and document.pages else 0,
                "has_document_layout": hasattr(document, 'document_layout') and bool(document.document_layout),
                "blocks_count": len(document.document_layout.blocks) if hasattr(document, 'document_layout') and document.document_layout else 0,
                "has_chunked_document": hasattr(document, 'chunked_document') and bool(document.chunked_document),
                "chunks_count": len(document.chunked_document.chunks) if hasattr(document, 'chunked_document') and document.chunked_document else 0,
                "has_images": hasattr(document, 'images') and bool(document.images),
                "images_count": len(document.images) if hasattr(document, 'images') and document.images else 0
            }
        }
        
        # document_layout.blocks詳細
        if hasattr(document, 'document_layout') and document.document_layout:
            blocks_detail = []
            for i, block in enumerate(document.document_layout.blocks):
                # バウンディングボックス情報を取得（正しい属性名を使用）
                bounding_box = None
                if hasattr(block, 'bounding_box') and block.bounding_box:
                    bbox = block.bounding_box
                    if hasattr(bbox, 'normalized_vertices') and bbox.normalized_vertices:
                        # 正規化座標（0-1の範囲）を取得
                        vertices = []
                        for vertex in bbox.normalized_vertices:
                            vertices.append({
                                "x": getattr(vertex, 'x', 0),
                                "y": getattr(vertex, 'y', 0)
                            })
                        bounding_box = {
                            "normalized_vertices": vertices
                        }
                    elif hasattr(bbox, 'vertices') and bbox.vertices:
                        # 絶対座標を取得
                        vertices = []
                        for vertex in bbox.vertices:
                            vertices.append({
                                "x": getattr(vertex, 'x', 0),
                                "y": getattr(vertex, 'y', 0)
                            })
                        bounding_box = {
                            "vertices": vertices
                        }
                
                block_info = {
                    "block_id": i + 1,
                    "has_text_block": hasattr(block, 'text_block') and bool(block.text_block),
                    "text": block.text_block.text if hasattr(block, 'text_block') and block.text_block else "",
                    "text_length": len(block.text_block.text) if hasattr(block, 'text_block') and block.text_block else 0,
                    "bounding_box": bounding_box  # バウンディングボックス情報を追加
                }
                blocks_detail.append(block_info)
            
            results["blocks_detail"] = blocks_detail
        
        # チャンキング結果詳細（重要な新機能）
        if hasattr(document, 'chunked_document') and document.chunked_document:
            chunks_detail = []
            for i, chunk in enumerate(document.chunked_document.chunks):
                chunk_content = getattr(chunk, 'content', '')
                chunk_page_headers = getattr(chunk, 'page_headers', [])
                
                # チャンクのバウンディングボックス情報を取得
                chunk_bounding_boxes = []
                if hasattr(chunk, 'source_block_ids') and chunk.source_block_ids:
                    # source_block_idsを確認
                    for block_id in chunk.source_block_ids:
                        chunk_bounding_boxes.append({"source_block_id": str(block_id)})
                
                # chunk内のparagraphsからもバウンディングボックス情報を取得
                paragraphs_with_bbox = []
                if hasattr(chunk, 'chunk_elements') and chunk.chunk_elements:
                    for elem_i, element in enumerate(chunk.chunk_elements):
                        if hasattr(element, 'layout') and element.layout:
                            if hasattr(element.layout, 'bounding_poly') and element.layout.bounding_poly:
                                bbox = element.layout.bounding_poly
                                if hasattr(bbox, 'normalized_vertices') and bbox.normalized_vertices:
                                    vertices = []
                                    for vertex in bbox.normalized_vertices:
                                        vertices.append({
                                            "x": getattr(vertex, 'x', 0),
                                            "y": getattr(vertex, 'y', 0)
                                        })
                                    paragraphs_with_bbox.append({
                                        "element_id": elem_i,
                                        "bounding_box": {"normalized_vertices": vertices}
                                    })
                
                chunk_info = {
                    "chunk_id": i + 1,
                    "content": chunk_content,
                    "content_length": len(chunk_content),
                    "page_headers_count": len(chunk_page_headers),
                    "page_headers": [str(header) for header in chunk_page_headers] if chunk_page_headers else [],
                    "source_blocks": chunk_bounding_boxes,  # ソースブロック情報
                    "element_bounding_boxes": paragraphs_with_bbox,  # 要素レベルのバウンディングボックス
                    "preview": chunk_content[:200] + "..." if len(chunk_content) > 200 else chunk_content
                }
                chunks_detail.append(chunk_info)
            
            results["chunks_detail"] = chunks_detail
            results["total_chunked_text_length"] = sum(len(getattr(chunk, 'content', '')) for chunk in document.chunked_document.chunks)
        
        # v1beta3 新機能結果の詳細記録
        
        # images情報詳細
        if hasattr(document, 'images') and document.images:
            images_detail = []
            for i, image in enumerate(document.images):
                image_info = {
                    "image_id": i + 1,
                    "type": type(image).__name__,
                    "has_content": hasattr(image, 'content') and bool(image.content),
                    "content_length": len(image.content) if hasattr(image, 'content') and image.content else 0
                }
                images_detail.append(image_info)
            
            results["images_detail"] = images_detail
        else:
            results["images_detail"] = []
        
        # pages詳細情報
        if hasattr(document, 'pages') and document.pages:
            pages_detail = []
            for i, page in enumerate(document.pages):
                page_info = {
                    "page_id": i + 1,
                    "page_number": getattr(page, 'page_number', i + 1),
                    "has_blocks": hasattr(page, 'blocks') and bool(page.blocks),
                    "blocks_count": len(page.blocks) if hasattr(page, 'blocks') and page.blocks else 0,
                    "has_paragraphs": hasattr(page, 'paragraphs') and bool(page.paragraphs),
                    "paragraphs_count": len(page.paragraphs) if hasattr(page, 'paragraphs') and page.paragraphs else 0,
                    "has_lines": hasattr(page, 'lines') and bool(page.lines),
                    "lines_count": len(page.lines) if hasattr(page, 'lines') and page.lines else 0,
                    "has_tables": hasattr(page, 'tables') and bool(page.tables),
                    "tables_count": len(page.tables) if hasattr(page, 'tables') and page.tables else 0
                }
                pages_detail.append(page_info)
            
            results["pages_detail"] = pages_detail
        else:
            results["pages_detail"] = []
        
        # v1beta3 機能検証結果サマリー
        results["v1beta3_features_summary"] = {
            "returnImages_detected": bool(hasattr(document, 'images') and document.images),
            "returnBoundingBoxes_detected": False,  # 座標情報が検出された場合はTrueに更新
            "enableImageAnnotation_active": bool(hasattr(document, 'pages') and document.pages and 
                                                any(hasattr(page, 'image_annotations') and page.image_annotations for page in document.pages)),
            "enableTableAnnotation_active": bool(hasattr(document, 'pages') and document.pages and 
                                               any(hasattr(page, 'tables') and page.tables for page in document.pages)),
            "enableLlmLayoutParsing_active": bool(hasattr(document, 'chunked_document') and document.chunked_document and 
                                                len(document.chunked_document.chunks) > 1)
        }
        
        # 適切なフィールド参照解析結果を追加
        results["analysis_results"] = field_reference_results
        
        # 🆕 個別画像切り抜き結果を追加
        results["individual_images"] = individual_images_summary
        
        # 🔬 image_block 詳細調査結果を追加
        results["image_block_investigation"] = image_block_investigation
        
        # 🎯 Layout Parser座標調査結果を追加
        results["layout_coordinates_investigation"] = layout_coordinates_summary
        
        # 結果をJSONファイルに保存
        output_file = "layout_parser_field_reference_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 詳細結果保存完了: {output_file}")
        print(f"   📊 解析データ:")
        print(f"      座標情報: {field_reference_results['summary']['total_coordinates']}個")
        print(f"      画像データ: {field_reference_results['summary']['total_images']}個") 
        print(f"      ビジュアル要素: {field_reference_results['summary']['total_visual_elements']}個")
        print(f"      チャンク数: {results['document_analysis']['chunks_count']}個")
        print(f"   🆕 個別画像切り抜き:")
        print(f"      切り抜き成功: {individual_images_summary['total_extracted']}個")
        print(f"   🔬 image_block 詳細調査:")
        print(f"      image_block保有ブロック: {image_block_investigation['blocks_with_image_block']}個")
        print(f"   🎯 Layout Parser座標調査:")
        print(f"      座標セット発見: {layout_coordinates_summary['total_coordinate_sets']}個")
        
        return results
        bbox_detected = False
        if hasattr(document, 'document_layout') and document.document_layout:
            for block in document.document_layout.blocks:
                if hasattr(block, 'bounding_box') and block.bounding_box:
                    if (hasattr(block.bounding_box, 'normalized_vertices') and block.bounding_box.normalized_vertices) or \
                       (hasattr(block.bounding_box, 'vertices') and block.bounding_box.vertices):
                        bbox_detected = True
                        break
        
        results["v1beta3_features_summary"]["returnBoundingBoxes_detected"] = bbox_detected
        
        # 結果保存
        output_file = "layout_parser_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 詳細結果保存: {output_file}")
        print(f"🔍 v1beta3機能検証サマリー:")
        print(f"   returnImages: {'✅ 検出' if results['v1beta3_features_summary']['returnImages_detected'] else '❌ なし'}")
        print(f"   returnBoundingBoxes: {'✅ 検出' if results['v1beta3_features_summary']['returnBoundingBoxes_detected'] else '❌ なし'}")
        print(f"   enableLlmLayoutParsing: {'✅ 有効' if results['v1beta3_features_summary']['enableLlmLayoutParsing_active'] else '❌ 無効'}")
        print(f"   pages詳細: {len(results['pages_detail'])}ページ")

if __name__ == "__main__":
    tester = LayoutParserTest()
    tester.analyze_layout_parser_result()